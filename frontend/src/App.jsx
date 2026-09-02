import { useState, useEffect, useRef } from "react";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import SynthesisPanel from "./components/SynthesisPanel";
import FollowUpChips from "./components/FollowUpChips";
import TurnActions from "./components/TurnActions";

// One entry per question asked. Turns accumulate so the thread scrolls
// instead of the previous answer being wiped on every follow-up.
function newTurn(id, query) {
  return { id, query, status: [], synthesis: null, error: null, loading: true };
}

/* Each turn sits against a rail: a numbered node with a hairline running down
   through the answer, so the page reads as one thread rather than stacked
   cards separated by empty space. */
function TurnRow({ index, isLast, children }) {
  return (
    <div
      className="turn-in"
      style={{
        maxWidth: 1040,
        margin: "0 auto",
        padding: "0 32px",
        display: "grid",
        gridTemplateColumns: "26px 1fr",
        columnGap: 22,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <span
          className="tnum"
          style={{
            width: 26,
            height: 26,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            color: "var(--text-secondary)",
            border: "1px solid var(--border)",
            background: "var(--bg-primary)",
            borderRadius: 999,
            flexShrink: 0,
            marginTop: 34,
          }}
        >
          {index + 1}
        </span>
        <div
          style={{
            flex: 1,
            width: 1,
            marginTop: 10,
            // The last rail fades out instead of stopping dead.
            background: isLast
              ? "linear-gradient(var(--border), transparent)"
              : "var(--border)",
          }}
        />
      </div>
      <div style={{ minWidth: 0, paddingBottom: isLast ? 24 : 56 }}>{children}</div>
    </div>
  );
}

function QuestionHeader({ query, isFollowUp }) {
  return (
    <h2
      style={{
        fontFamily: "var(--font-serif)",
        // Follow-ups are answers to the turn above, so they sit quieter than
        // the question that opened the thread.
        fontSize: isFollowUp ? 18 : 24,
        fontWeight: 600,
        color: "var(--text-primary)",
        lineHeight: 1.35,
        margin: "32px 0 0",
        letterSpacing: "-0.01em",
        maxWidth: "46ch",
      }}
    >
      {isFollowUp && (
        <span style={{ color: "var(--text-secondary)", marginRight: 8, fontWeight: 400 }}>
          ↳
        </span>
      )}
      {query}
    </h2>
  );
}

function ErrorBanner({ message }) {
  return (
    <div
      style={{
        marginTop: 20,
        padding: "16px 20px",
        borderRadius: 10,
        border: "1px solid var(--contradiction-border)",
        background: "var(--contradiction-bg)",
        fontSize: 14,
        color: "var(--text-primary)",
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <span style={{ color: "var(--contradiction-border)" }}>✕</span>
      {message === "Failed to fetch"
        ? "Backend unreachable. Make sure the server is running on port 8000."
        : message}
    </div>
  );
}

const STORE_KEY = "tarka.thread.v1";

// Restoring in a lazy initialiser rather than an effect: an effect would run
// after the first render and race with the empty initial state.
function loadStored() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed.turns)) return null;
    return parsed;
  } catch {
    return null; // private mode, quota, or a stale shape — start fresh
  }
}

export default function App() {
  const stored = useRef(loadStored()).current;

  const [theme, setTheme] = useState("dark");
  // A half-finished turn shouldn't come back as permanently loading.
  const [turns, setTurns] = useState(() =>
    (stored?.turns ?? []).map((t) => ({ ...t, loading: false }))
  );
  const [loading, setLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState(
    () => stored?.conversationHistory ?? []
  );
  // Held once at the top level rather than inside every turn: the payload
  // echoes the same ~37KB of sources back on each follow-up.
  const [corpus, setCorpus] = useState(
    () => stored?.corpus ?? { web: [], papers: [] }
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const lastTurnRef = useRef(null);

  // Scroll when a turn is *added*, not as its content streams in — scrolling
  // on every payload update makes the page jump around while it loads.
  useEffect(() => {
    if (turns.length > 0 && lastTurnRef.current) {
      lastTurnRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [turns.length]);

  // Persist the thread so a refresh doesn't destroy it. Skipped mid-request:
  // there's no value in storing a turn that's still streaming.
  useEffect(() => {
    if (loading) return;
    try {
      if (turns.length === 0) localStorage.removeItem(STORE_KEY);
      else
        localStorage.setItem(
          STORE_KEY,
          JSON.stringify({ turns, corpus, conversationHistory })
        );
    } catch {
      // Quota exceeded or storage unavailable — the thread still works in
      // memory, it just won't survive a refresh.
    }
  }, [turns, corpus, conversationHistory, loading]);

  function patchTurn(id, fn) {
    setTurns((prev) => prev.map((t) => (t.id === id ? fn(t) : t)));
  }

  function clearThread() {
    setTurns([]);
    setConversationHistory([]);
    setCorpus({ web: [], papers: [] });
    try {
      localStorage.removeItem(STORE_KEY);
    } catch {
      /* nothing to clean up */
    }
  }

  async function handleSearch(searchQuery) {
    if (loading) return; // one request at a time; the input is disabled too

    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setTurns((prev) => [...prev, newTurn(id, searchQuery)]);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: searchQuery,
          conversation_history: conversationHistory,
          previous_web_results: corpus.web,
          previous_paper_results: corpus.papers,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // Network chunks don't align to line boundaries — a single SSE frame can
      // arrive split across two reads. Buffer the tail until it's a whole line,
      // otherwise both halves fail JSON.parse and the event is lost silently.
      let buffer = "";
      let streaming = true;

      while (streaming) {
        const { done, value } = await reader.read();

        if (done) {
          buffer += decoder.decode(); // flush any trailing bytes
          streaming = false;
        } else {
          buffer += decoder.decode(value, { stream: true });
        }

        const lines = buffer.split("\n");
        // While the stream is live the last piece may be a partial line, so
        // hold it back for the next read. Once closed, everything is complete.
        buffer = streaming ? lines.pop() : "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          let event;
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue; // malformed line, skip it
          }

          if (event.type === "status") {
            patchTurn(id, (t) => ({ ...t, status: [...t.status, event.message] }));
          }
          if (event.type === "error") {
            patchTurn(id, (t) => ({ ...t, error: event.message }));
            return;
          }
          if (event.type === "result") {
            // Keep the sources out of the turn — they're identical every turn.
            const { web_results, paper_results, ...synthesis } = event.payload;
            setCorpus({ web: web_results || [], papers: paper_results || [] });
            patchTurn(id, (t) => ({ ...t, synthesis }));
            // One entry per turn, findings only — the Critic uses these to
            // resolve references and avoid repeating itself, never as evidence.
            setConversationHistory((prev) => [
              ...prev,
              {
                question: searchQuery,
                summary: synthesis.summary,
                consensus_points: (synthesis.consensus || [])
                  .map((c) => c.point)
                  .filter(Boolean),
                contradiction_topics: (synthesis.contradictions || [])
                  .map((c) => c.conflict_topic)
                  .filter(Boolean),
              },
            ]);
          }
          if (event.type === "done") {
            streaming = false;
          }
        }
      }
    } catch (err) {
      patchTurn(id, (t) => ({ ...t, error: err.message }));
    } finally {
      // Runs on every exit path — normal end, thrown error, or the early
      // return above — so a turn can't stay stuck loading.
      patchTurn(id, (t) => ({ ...t, loading: false }));
      setLoading(false);
    }
  }

  return (
    // No background here — body paints it, and an opaque fill at this level
    // would cover the body::before dot texture.
    <div style={{ minHeight: "100vh" }}>
      {/* Theme toggle + thread reset */}
      <div
        className="no-print"
        style={{ position: "absolute", top: 20, right: 24, display: "flex", gap: 8 }}
      >
        {turns.length > 0 && !loading && (
          <button
            onClick={clearThread}
            title="Clear this thread and start over"
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              borderRadius: 8,
              padding: "6px 14px",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Clear
          </button>
        )}
        <button
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
            borderRadius: 8,
            padding: "6px 14px",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>

      <SearchBar
        onSearch={handleSearch}
        hasResults={turns.length > 0}
        disabled={loading}
      />

      {turns.map((turn, i) => {
        const isLast = i === turns.length - 1;
        return (
          <div key={turn.id} ref={isLast ? lastTurnRef : null}>
            <TurnRow index={i} isLast={isLast}>
              <QuestionHeader query={turn.query} isFollowUp={i > 0} />

              {turn.loading && !turn.synthesis && <StatusBar messages={turn.status} />}
              {turn.synthesis && (
                <>
                  <SynthesisPanel synthesis={turn.synthesis} sources={corpus} />
                  <TurnActions turn={turn} sources={corpus} />
                </>
              )}
              {turn.error && <ErrorBanner message={turn.error} />}

              {/* Chips only under the newest answer — offering them on older
                  turns would branch the thread, which conversation_history
                  (a flat list) can't represent. */}
              {isLast && !turn.loading && turn.synthesis && (
                <FollowUpChips
                  followups={turn.synthesis.suggested_followups}
                  onSelect={handleSearch}
                />
              )}
            </TurnRow>
          </div>
        );
      })}

      <div style={{ height: 80 }} />
    </div>
  );
}
