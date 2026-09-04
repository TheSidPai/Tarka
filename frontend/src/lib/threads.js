// Multi-thread storage. Threads are kept newest-first and capped, because the
// corpus alone is ~48KB per thread and localStorage is a ~5MB budget.

const KEY = "tarka.threads.v1";
const LEGACY_KEY = "tarka.thread.v1"; // single-thread format that shipped first
export const MAX_THREADS = 8;

function safeParse(raw) {
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function loadThreads() {
  try {
    const parsed = safeParse(localStorage.getItem(KEY));
    if (Array.isArray(parsed?.threads)) return parsed.threads;

    // Migrate a thread saved under the old single-slot key.
    const legacy = safeParse(localStorage.getItem(LEGACY_KEY));
    if (Array.isArray(legacy?.turns) && legacy.turns.length) {
      const migrated = [{
        id: `legacy-${Date.now()}`,
        title: legacy.turns[0]?.query ?? "Untitled",
        updatedAt: Date.now(),
        turns: legacy.turns,
        corpus: legacy.corpus ?? { web: [], papers: [] },
        conversationHistory: legacy.conversationHistory ?? [],
      }];
      saveThreads(migrated);
      localStorage.removeItem(LEGACY_KEY);
      return migrated;
    }
  } catch {
    // private mode, or storage disabled
  }
  return [];
}

export function saveThreads(threads) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ threads: threads.slice(0, MAX_THREADS) }));
    return true;
  } catch {
    // Almost certainly the quota. Drop the oldest and try once more before
    // giving up — losing old threads beats losing the current one.
    try {
      localStorage.setItem(
        KEY,
        JSON.stringify({ threads: threads.slice(0, Math.max(1, Math.floor(MAX_THREADS / 2))) })
      );
      return true;
    } catch {
      return false;
    }
  }
}

export function upsertThread(threads, thread) {
  const rest = threads.filter((t) => t.id !== thread.id);
  return [{ ...thread, updatedAt: Date.now() }, ...rest].slice(0, MAX_THREADS);
}

/* ---- Server sync ------------------------------------------------------
   The server is a durable mirror, not the source of truth for a live
   session: a failed sync must never block the UI, so every call below
   resolves rather than throws. localStorage keeps working offline; the
   server is what makes a thread survive a different browser. */

const API = "http://localhost:8000";

export function newThreadId() {
  // Server-side identity with no user table: an unguessable id makes a
  // thread shareable. Shareable is not private — anyone with the link reads it.
  return crypto.randomUUID?.() ?? `t-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export async function pushThread(thread) {
  try {
    const res = await fetch(`${API}/api/threads/${thread.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: thread.title ?? "",
        payload: {
          turns: thread.turns,
          corpus: thread.corpus,
          conversationHistory: thread.conversationHistory,
        },
      }),
    });
    return res.ok;
  } catch {
    return false; // offline, or the backend isn't running
  }
}

export async function pullThread(id) {
  try {
    const res = await fetch(`${API}/api/threads/${id}`);
    if (!res.ok) return null;
    const row = await res.json();
    return {
      id: row.id,
      title: row.title,
      updatedAt: (row.updated_at ?? Date.now() / 1000) * 1000,
      turns: row.payload?.turns ?? [],
      corpus: row.payload?.corpus ?? { web: [], papers: [] },
      conversationHistory: row.payload?.conversationHistory ?? [],
    };
  } catch {
    return null;
  }
}

export function threadIdFromUrl() {
  try {
    return new URLSearchParams(window.location.search).get("t");
  } catch {
    return null;
  }
}

export function setUrlThread(id) {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("t", id);
    window.history.replaceState({}, "", url);
  } catch {
    /* history unavailable — the link just won't update */
  }
}

export function shareUrl(id) {
  const url = new URL(window.location.href);
  url.searchParams.set("t", id);
  return url.toString();
}

export function relativeTime(ts) {
  const mins = Math.floor((Date.now() - ts) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
