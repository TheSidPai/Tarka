import { useState, useEffect, useRef } from "react";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import SynthesisPanel from "./components/SynthesisPanel";
import FollowUpChips from "./components/FollowUpChips";

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState([]);
  const [synthesis, setSynthesis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [error, setError] = useState(null);
  const [lastResults, setLastResults] = useState({ web: [], papers: [] });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const synthesisRef = useRef(null);

  useEffect(() => {
    if (synthesis && synthesisRef.current) {
      synthesisRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [synthesis]);

  async function handleSearch(searchQuery) {
    setQuery(searchQuery);
    setSynthesis(null);
    setStatus([]);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: searchQuery,
          conversation_history: conversationHistory,
          previous_web_results: lastResults.web,
          previous_paper_results: lastResults.papers,
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
            setStatus((prev) => [...prev, event.message]);
          }
          if (event.type === "error") {
            setError(event.message);
            return;
          }
          if (event.type === "result") {
            console.log("Payload received:", event.payload);
            console.log("Follow-ups:", event.payload.suggested_followups);
            setSynthesis(event.payload);
            setLastResults({
              web: event.payload.web_results || [],
              papers: event.payload.paper_results || [],
            });
            setConversationHistory((prev) => [
              ...prev,
              { role: "user", content: searchQuery },
              {
                role: "assistant",
                content: JSON.stringify(event.payload.summary),
              },
            ]);
          }
          if (event.type === "done") {
            streaming = false;
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      // Runs on every exit path — normal end, thrown error, or the early
      // return above — so the spinner can't outlive the request.
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
        hasResults={!!synthesis || loading}
        value={query}
      />

      {status.length > 0 && !synthesis && <StatusBar messages={status} />}
      {synthesis && (
        <>
          <div ref={synthesisRef}>
            <SynthesisPanel synthesis={synthesis} />
          </div>
          <FollowUpChips
            followups={synthesis.suggested_followups}
            onSelect={handleSearch}
          />
        </>
      )}

      {error && (
        <div
          style={{
            maxWidth: 720,
            margin: "32px auto 0",
            padding: "0 24px",
          }}
        >
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
            {error === "Failed to fetch"
              ? "Backend unreachable. Make sure the server is running on port 8000."
              : error}
          </div>
        </div>
      )}
    </div>
  );
}
