# Tarka — Build Timeline

```
Days 1-2: Get data in
  Web Scout (Tavily) + Paper Scout (ArXiv)

Day 3: Control flow
  Orchestrator + conditional routing

Days 4-5: The interesting part
  Critic (contradictions) + Synthesizer (clean output)

Days 6-7: Make it a real service
  Memory layer + FastAPI + SSE streaming

Days 8-10: Put a face on it
  React UI + error handling + polish
```

---

## Day 1 — LangGraph setup + Web Scout
Set up the project layout, define `TarkaState`, wire up Tavily, compile the first single-node graph. By end of day, you can pass a query in and get structured web results out.

## Day 2 — Paper Scout
Add the ArXiv tool as a separate node. By end of day, the same query returns both web results and paper abstracts side by side. You'll already see disagreements between them manually — that's the whole motivation for Day 4.

## Day 3 — Orchestrator + Conditional Routing
Pull control flow into a dedicated Orchestrator node. It sets a `needs_fetch` flag — follow-up queries skip the scouts entirely and go straight to the Synthesizer. This is what makes multi-turn conversation efficient.

## Day 4 — Critic Node
The hardest and most interesting day. The Critic receives both scouts' outputs, cross-examines them, and returns structured `contradictions` and `consensus` arrays — each claim grounded in a cited source. No hallucinated contradictions; the prompt requires quoting the exact source text before flagging a conflict.

## Day 5 — Synthesizer + Output Schema
Define a Pydantic model for the final synthesis object. The Synthesizer takes the full graph state and produces locked JSON — summary, consensus points, contradiction pairs, confidence level, suggested follow-ups. After Day 5, the full pipeline runs locally end-to-end.

## Day 6 — Memory Layer
Add `conversation_history` to state. The Orchestrator checks whether an incoming query is a follow-up — if it is, skip re-fetching and use existing synthesis as context. Two-turn conversation works by end of day.

## Day 7 — FastAPI + SSE Streaming
Expose the graph over HTTP. Use `graph.astream()` inside a FastAPI `StreamingResponse` so the frontend gets live node-completion events as the graph runs. Add session management endpoints (`GET /history`, `DELETE /session`).

## Day 8 — React Frontend
Build the UI component tree first (on paper), then code. Components: `QueryInput`, `StatusBar`, `SynthesisPanel` (with `ConsensusSection` and `ContradictionSection`), `CitationsPanel`, `FollowUpSuggestions`. Wire to backend SSE stream.

## Day 9 — Error Handling + Resilience
Defensive passes: Tavily failure → continue on papers only. ArXiv zero results → flag low confidence. Critic returns malformed JSON → catch and re-prompt once. Frontend stream drops → friendly error boundary. Add per-session rate limiting so APIs don't get hammered.

## Day 10 — Documentation + Demo Prep
Fill in the metrics table (run 5 real queries, record latencies). Write `DEMO.md` with 3 curated queries where web and papers genuinely disagree. Finalize Mermaid architecture diagram. Containerize with `docker-compose.yml`. Push clean commit history.
