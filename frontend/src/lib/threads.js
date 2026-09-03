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

export function relativeTime(ts) {
  const mins = Math.floor((Date.now() - ts) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
