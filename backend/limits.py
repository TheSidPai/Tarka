# backend/limits.py
"""Protecting /api/research from being an expensive button for strangers.

Two separate defences, because they guard different things:

  * a per-IP token bucket, so one client can't run a hundred queries an hour;
  * a global concurrency semaphore, because the scarce resource here isn't
    request rate. A single research run holds an SSE connection for ~20s and
    makes two LLM calls over ~40KB of context, so fifty simultaneous requests
    would pin fifty graph runs regardless of how the hourly limit is set.

In-process on purpose. Lua-in-Redis exists to make check-and-increment atomic
across *distributed* workers; with one uvicorn process the event loop is
single-threaded, so a critical section containing no `await` cannot interleave
— atomicity by construction. `_take()` below is synchronous for exactly that
reason and must stay that way.

That guarantee dies the moment this runs as `uvicorn --workers N` or behind a
load balancer with more than one container: each worker would keep its own
bucket and the effective limit would be N times the configured one. That is
the point at which this file should be replaced by Redis and an EVAL script,
not before.
"""
import os
import time
from collections import OrderedDict

RATE_LIMIT = int(os.environ.get("TARKA_RATE_LIMIT", "12"))          # requests
RATE_WINDOW = float(os.environ.get("TARKA_RATE_WINDOW", "3600"))    # seconds
MAX_CONCURRENT = int(os.environ.get("TARKA_MAX_CONCURRENT", "4"))
MAX_TRACKED_CLIENTS = 4096  # bounded so the table can't grow without limit

# client -> (tokens, last_refill). OrderedDict so the oldest entry can be
# evicted in O(1) when the table is full.
_buckets: "OrderedDict[str, tuple[float, float]]" = OrderedDict()

_in_flight = 0


def _take(client: str) -> tuple[bool, int]:
    """Spend one token. Returns (allowed, retry_after_seconds).

    Synchronous and await-free — see the module docstring. Do not make this a
    coroutine or add I/O to it.
    """
    now = time.monotonic()
    rate = RATE_LIMIT / RATE_WINDOW  # tokens per second

    tokens, last = _buckets.get(client, (float(RATE_LIMIT), now))
    tokens = min(float(RATE_LIMIT), tokens + (now - last) * rate)

    if tokens < 1.0:
        _buckets[client] = (tokens, now)
        _buckets.move_to_end(client)
        # Time until one whole token has accrued.
        return False, max(1, int((1.0 - tokens) / rate))

    _buckets[client] = (tokens - 1.0, now)
    _buckets.move_to_end(client)
    while len(_buckets) > MAX_TRACKED_CLIENTS:
        _buckets.popitem(last=False)
    return True, 0


def check(client: str) -> tuple[bool, int]:
    return _take(client)


def slots_free() -> bool:
    return _in_flight < MAX_CONCURRENT


def acquire() -> None:
    global _in_flight
    _in_flight += 1


def release() -> None:
    global _in_flight
    _in_flight = max(0, _in_flight - 1)


def snapshot() -> dict:
    return {
        "in_flight": _in_flight,
        "max_concurrent": MAX_CONCURRENT,
        "tracked_clients": len(_buckets),
        "limit": RATE_LIMIT,
        "window_seconds": RATE_WINDOW,
    }
