# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tarka is a multi-agent research assistant. A query fans out to the open web (Tavily) and academic literature (OpenAlex), an adversarial Critic LLM cross-examines the two source sets for consensus and contradictions, and a Synthesizer packages the result. The backend is FastAPI + LangGraph streaming SSE; the frontend is React + Vite consuming that stream.

## Commands

```bash
# Backend via Docker (reads root .env for API keys)
docker compose up -d --build          # → http://localhost:8000/api/research

# Backend without Docker — MUST run from backend/, imports are top-level
cd backend && pip install -r requirements.txt
python server.py                      # uvicorn with reload on :8000
python main.py                        # run the graph once, headless, prints final_payload

# Frontend
cd frontend && npm install
npm run dev                           # → http://localhost:5173
npm run lint                          # eslint
npm run build
```

There is no test suite. `backend/main.py` is the de-facto harness: edit `turn_1_state` in it to exercise the graph without the server or the UI. It has a commented-out fixture with fake contradicting web/paper results — useful for testing the Critic and Synthesizer without network calls.

`.env` at the repo root (not in `backend/`) supplies `TAVILY_API_KEY` and `ANTHROPIC_API_KEY`; docker-compose passes it into the container. `SEMANTIC_SCHOLAR_API_KEY` in `.env.example` is vestigial — see dead code below.

## Architecture

The whole backend is a single compiled LangGraph in [backend/graph/graph.py](backend/graph/graph.py). `TarkaState` ([backend/graph/state.py](backend/graph/state.py)) is a flat TypedDict that every node reads from and returns partial updates into. Nodes are plain sync functions, not LangChain agents.

```
START → orchestrator ──needs_fetch=True──→ web_scout → paper_scout ──┐
                     └──needs_fetch=False─────────────────────────→ critic → synthesizer → END
```

Three design decisions dominate the code and are worth preserving:

**The Critic never emits JSON.** Forcing structured output while the model does deep logical inversion caused silently dropped arrays. So [critic_twopass.py](backend/agents/critic_twopass.py) has the model think freely inside XML tags, then extracts with `re.findall` / `extract_tag`. If you change the Critic's prompt, the tag names in the prompt and the regex extractors must stay in lockstep — nothing validates them against each other, a rename just yields empty lists.

**The Synthesizer does zero reasoning.** [synthesizer.py](backend/agents/synthesizer.py) is the only node using `.with_structured_output()`, and only because it just remaps already-computed state into `TarkaResponseSchema`. `source_count` is computed natively in Python, not by the model. This node's schema is the UI contract — changing it breaks [SynthesisPanel.jsx](frontend/src/components/SynthesisPanel.jsx).

**The hallucination guard is load-bearing.** The Critic returns early with empty lists if *either* `web_results` or `paper_results` is empty. A model cross-examining one source set invents the opposing side. Scouts swallow their own exceptions and return `[]`, so an API failure reaches the Critic as an empty list, not an error — that early return is the only thing standing between a dead API key and fabricated contradictions.

**Follow-ups skip the network entirely.** [orchestrator.py](backend/agents/orchestrator.py) sets `needs_fetch=False` whenever `conversation_history` is non-empty, routing straight to the Critic. Sessions are stateless server-side: the React client holds `lastResults` and `conversationHistory` and posts them back as `previous_web_results` / `previous_paper_results` on every request ([App.jsx](frontend/src/App.jsx)). A page refresh wipes memory.

### Streaming contract

[server.py](backend/server.py) iterates `graph.astream()` and yields four SSE event shapes: `status` (once per completed node), `result` (only when `synthesizer` produces `final_payload`), `error`, `done`. The frontend parses these by hand from a `fetch` ReadableStream, splitting on `\n` and stripping the `data: ` prefix — it does not use `EventSource`. Adding a graph node automatically produces a new `status` event; adding a new *event type* requires matching branches in both files.

CORS is hardcoded to `http://localhost:5173`, and the frontend's API URL is hardcoded to `http://localhost:8000` — both need changing together for any non-local run.

### Dead code

`graph.py` imports `critic_node` and `critic_node_split` from [critic.py](backend/agents/critic.py) but registers `critic_two_pass_node` as the `"critic"` node. Those two are earlier structured-output attempts, kept deliberately as a record of what failed. Also unused: `backend/agents/paper_scout_ss.py` (Semantic Scholar, replaced by OpenAlex for its better semantic search) — likewise kept on purpose. Don't "clean up" either one.

Every LLM call is `claude-haiku-4-5-20251001` via `langchain_anthropic`; the paper scout uses plain `requests` against OpenAlex. `langchain-anthropic` is pinned to `0.1.23` and must stay `<0.2` — later releases need `langchain-core>=0.3`, which conflicts with the pinned `langgraph==0.1.4` / `langchain==0.2.5`. `tavily-python` is unrelated to that ceiling and pinned to `0.8.0`; it must stay `>=0.7` because [web_scout.py](backend/agents/web_scout.py) passes `search_depth="fast"`, which older clients reject.

Tavily's `search_depth` controls snippets extracted *per URL*, not the number of URLs — it's the volume dial, not `max_results`. `fast` yields ~7x the text per source over `basic` at the same 1-credit cost, which is what keeps the web corpus at parity with OpenAlex abstracts so the Critic has comparable evidence on both sides. Don't switch to `include_raw_content`: it returns ~25x the text as raw page dumps, and diluting the Critic's context is the exact failure this project is built to avoid.

### Frontend

Vite + React 19, Tailwind v4 via `@tailwindcss/vite`. Components style themselves with inline styles referencing CSS custom properties defined in [index.css](frontend/src/index.css); theming works by setting `data-theme` on `documentElement`. Follow that pattern rather than introducing Tailwind utility classes into existing components.

## Documentation

[docs/project_documentation.md](docs/project_documentation.md) is a day-by-day build log explaining why each layer exists — including the failed approaches. Its architecture table is partly stale (it lists ArXiv and GPT-4o; the code uses OpenAlex and Claude Haiku). Trust the code over the docs on stack details, and the docs over the code on rationale.
