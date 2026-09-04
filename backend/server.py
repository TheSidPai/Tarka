import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uvicorn
import time

# Import your graph builder
import limits
import store
from graph.graph import build_graph

# Initialize the app and the LangGraph engine
app = FastAPI(title="Tarka Research API")
graph = build_graph()


@app.on_event("startup")
async def _startup():
    await store.init()

# Enable CORS so your React frontend (localhost:5173) can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # For production, lock this down to your exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST SCHEMA ---
class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    conversation_history: List[Dict[str, Any]] = []
    previous_web_results: List[Dict[str, Any]] = []
    previous_paper_results: List[Dict[str, Any]] = []


class ThreadBody(BaseModel):
    title: str = ""
    payload: Dict[str, Any]


def client_key(request: Request) -> str:
    """Identify the caller for rate limiting.

    X-Forwarded-For is only meaningful behind a proxy you control — it is
    trivially spoofed otherwise, so it's read only when TARKA_TRUST_PROXY is
    set rather than by default.
    """
    import os
    if os.environ.get("TARKA_TRUST_PROXY"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# --- SSE GENERATOR ---
async def run_research_stream(request: ResearchRequest):
    """
    Executes the LangGraph pipeline and yields JSON updates after every node.
    """
    now = time.time()

    # Node completions and the Critic's live summary tokens arrive on different
    # timescales, so both are funnelled onto one queue and drained in order.
    # Without this the generator would be blocked awaiting the next astream()
    # step while the Critic spends ~10s generating.
    events: asyncio.Queue = asyncio.Queue()

    initial_state = {
        "query": request.query,
        "web_results": request.previous_web_results,
        "paper_results": request.previous_paper_results,
        "conversation_history": request.conversation_history,
        "needs_fetch": False,
        "consensus": [],
        "contradictions": [],
        "overall_summary": "",
        "final_payload": {},
        "_partial_queue": events,
    }

    async def run_graph():
        try:
            async for step in graph.astream(initial_state):
                # step is a dict like {"web_scout": {"web_results": [...]}}
                for node_name, node_update in step.items():
                    await events.put(("step", (node_name, node_update)))
        except Exception as e:
            await events.put(("error", str(e)))
        finally:
            await events.put(("finished", None))

    task = asyncio.create_task(run_graph())

    try:
        while True:
            kind, data = await events.get()

            if kind == "partial":
                # The Critic's summary as it writes it — cosmetic, and replaced
                # wholesale when the authoritative result arrives.
                yield f"data: {json.dumps({'type': 'partial', 'summary': data})}\n\n"

            elif kind == "step":
                node_name, node_update = data
                # astream() yields a step once the node has finished, so this is
                # past tense — the work is already done by the time it goes out.
                # Built outside the f-string: nested quotes across lines is
                # Python 3.12+ syntax, and the image runs 3.11.
                status_message = {
                    "type": "status",
                    "node": node_name,
                    "message": f"{node_name.replace('_', ' ').capitalize()} complete",
                }
                yield f"data: {json.dumps(status_message)}\n\n"

                if node_name == "synthesizer" and "final_payload" in node_update:
                    result_message = {
                        "type": "result",
                        "payload": node_update["final_payload"],
                    }
                    yield f"data: {json.dumps(result_message)}\n\n"

            elif kind == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': data})}\n\n"

            elif kind == "finished":
                break

        print("Time taken for research: {:.2f} seconds".format(time.time() - now))
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        if not task.done():
            task.cancel()
        # Released here rather than in the endpoint: the endpoint returns as
        # soon as the StreamingResponse is constructed, long before the run
        # is actually over.
        limits.release()


# --- API ENDPOINT ---
@app.post("/api/research")
async def research_endpoint(request: ResearchRequest, http: Request):
    """
    Returns a StreamingResponse that keeps the HTTP connection open
    and pushes events as they happen.
    """
    client = client_key(http)

    allowed, retry_after = limits.check(client)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit reached — {limits.RATE_LIMIT} searches per hour. "
                f"Try again in about {max(1, retry_after // 60)} minute(s)."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    # The real scarcity: each run holds a connection for ~20s and two LLM calls.
    if not limits.slots_free():
        raise HTTPException(
            status_code=503,
            detail="Too many searches running right now. Try again in a moment.",
            headers={"Retry-After": "20"},
        )

    limits.acquire()
    print(f"Received research request: {request.query}")
    return StreamingResponse(
        run_research_stream(request),
        media_type="text/event-stream"
    )


# --- THREAD PERSISTENCE ---
# No auth: the client generates the id and an unguessable id makes a thread
# shareable, not private. Adding accounts later means a user_id column here,
# not a rewrite.
@app.put("/api/threads/{thread_id}")
async def save_thread(thread_id: str, body: ThreadBody):
    if not store.valid_id(thread_id):
        raise HTTPException(status_code=400, detail="Malformed thread id.")
    try:
        return await store.save(thread_id, body.title, body.payload)
    except ValueError:
        raise HTTPException(status_code=413, detail="Thread too large to save.")


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    if not store.valid_id(thread_id):
        raise HTTPException(status_code=400, detail="Malformed thread id.")
    thread = await store.load(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="No such thread.")
    return thread


@app.delete("/api/threads/{thread_id}")
async def remove_thread(thread_id: str):
    if not store.valid_id(thread_id):
        raise HTTPException(status_code=400, detail="Malformed thread id.")
    if not await store.delete(thread_id):
        raise HTTPException(status_code=404, detail="No such thread.")
    return Response(status_code=204)


@app.get("/api/health")
async def health():
    return {"status": "ok", "limits": limits.snapshot()}


if __name__ == "__main__":

    # Run the server on port 8000
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)