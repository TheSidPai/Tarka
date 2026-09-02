import { useState, useEffect, useRef } from "react";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import SynthesisPanel from "./components/SynthesisPanel";
import FollowUpChips from "./components/FollowUpChips";

// One entry per question asked. Turns accumulate so the thread scrolls
// instead of the previous answer being wiped on every follow-up.
function newTurn(id, query) {
  return { id, query, status: [], synthesis: null, error: null, loading: true };
}

function QuestionHeader({ query, index }) {
  return (
    <div
      style={{
        maxWidth: 720,
        margin: "40px auto 0",
        padding: "0 24px",
        display: "flex",
        alignItems: "baseline",
        gap: 12,
      }}
    >
      <span
        style={{
          fontSize: 12,
          color: "var(--text-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          padding: "2px 7px",
          flexShrink: 0,
        }}
      >
        {index + 1}
      </span>
      <h2
        style={{
          fontSize: 19,
          fontWeight: 600,
          color: "var(--text-primary)",
          lineHeight: 1.4,
          margin: 0,
        }}
      >
        {query}
      </h2>
    </div>
  );
}

function ErrorBanner({ message }) {
  return (
    <div style={{ maxWidth: 720, margin: "24px auto 0", padding: "0 24px" }}>
      <div
        style={{
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
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [turns, setTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  // Held once at the top level rather than inside every turn: the payload
  // echoes the same ~37KB of sources back on each follow-up.
  const [corpus, setCorpus] = useState({ web: [], papers: [] });

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

  function patchTurn(id, fn) {
    setTurns((prev) => prev.map((t) => (t.id === id ? fn(t) : t)));
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
            setConversationHistory((prev) => [
              ...prev,
              { role: "user", content: searchQuery },
              { role: "assistant", content: JSON.stringify(event.payload.summary) },
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
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* Theme toggle */}
      <div style={{ position: "absolute", top: 20, right: 24 }}>
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
            <QuestionHeader query={turn.query} index={i} />

            {turn.loading && !turn.synthesis && <StatusBar messages={turn.status} />}
            {turn.synthesis && <SynthesisPanel synthesis={turn.synthesis} />}
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
          </div>
        );
      })}

      <div style={{ height: 80 }} />
    </div>
  );
}
