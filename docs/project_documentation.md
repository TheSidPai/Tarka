# Tarka (तर्क) — Project Documentation

## 1. What Tarka Is

**Tarka** is a multi-agent AI research assistant that takes an AI/ML question, searches the open web and academic papers simultaneously, finds where they agree and where they contradict each other, and lets you interrogate the synthesis interactively.

Named after *Tarka* (तर्क) — the tool of logical inference in Nyāya philosophy. The Nyāya school used tarka specifically to expose contradictions in a position and thereby get closer to truth. That's exactly what the Critic agent does.

### The Problem It Solves

When you research any AI/ML topic today, you're juggling browser tabs across blog posts, Twitter threads, and ArXiv abstracts. They frequently contradict each other — and nobody tells you that. A paper from 2024 might show LLMs fail at planning tasks while every popular blog says they reason well. You only discover this if you happen to read both carefully.

Tarka automates that cross-referencing layer and makes the disagreements explicit and citable.

### Architecture

Five nodes connected as a LangGraph state graph:

```
User Query
    ↓
Orchestrator       ← decides whether to fetch or use existing context
    ↓         ↓
Web Scout   Paper Scout    ← run sequentially (parallel-ready later)
    ↓         ↓
        Critic             ← finds contradictions and consensus
          ↓
      Synthesizer          ← produces structured JSON output
          ↓
    Memory Layer           ← stores conversation history for follow-ups
          ↓
       FastAPI
          ↓
       React UI
```

| Node | What it does | Tool |
|---|---|---|
| Orchestrator | Routes the query, sets `needs_fetch` flag | — |
| Web Scout | Fetches open-web claims | Tavily API |
| Paper Scout | Fetches paper abstracts and findings | ArXiv API |
| Critic | Cross-examines both, flags contradictions and consensus | LLM |
| Synthesizer | Packages everything into a typed JSON schema | LLM + Pydantic |

### Tech Stack

| Layer | Choice |
|---|---|
| Agent framework | LangGraph + LangChain |
| LLM | OpenAI GPT-4o / or other |
| Web search | Tavily API |
| Academic search | `arxiv` Python package |
| Backend | FastAPI + SSE streaming |
| Frontend | React + Tailwind (Vite) |
| Memory | In-context conversation history (per session) |

---

## Day 1 — Infrastructure + Web Scout

### Goal
Get the project skeleton up, define the shared state contract, wire up Tavily, and compile the first working graph. By end of day: pass a query in, get structured web results out.

### What Was Built

#### A. Shared State — `backend/graph/state.py`

The state is a `TypedDict` — a shared dictionary that every node reads from and writes back to. Nodes only return the keys they update; LangGraph merges those updates into the running state automatically.

Day 1 only needs two fields. The rest get added incrementally as we build each node.

```python
from typing import TypedDict, List, Dict, Any

class TarkaState(TypedDict):
    query: str
    web_results: List[Dict[str, Any]]
```

#### B. Web Scout Node — `backend/agents/web_scout.py`

This node takes the query from state, calls Tavily, and normalizes the response into a consistent shape: `url`, `title`, `claim`, `date`. It returns only `web_results` — the Orchestrator handles the rest.

Tavily is used instead of raw Google because it's purpose-built for LLM agents — it returns clean, pre-extracted text rather than raw HTML, which means we skip a whole parsing layer.

```python
def web_scout_node(state: TarkaState) -> dict:
    response = tavily_client.search(
        query=state["query"],
        max_results=5,
        include_raw_content=False
    )
    results = [
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "claim": item.get("content"),
            "date": item.get("published_date", "Unknown")
        }
        for item in response.get("results", [])
    ]
    return {"web_results": results}
```

#### C. Graph Assembly — `backend/graph/graph.py`

A minimal LangGraph: `START → web_scout → END`. One node, one edge. This is intentionally small — the graph grows one node at a time across Days 2-5.

```python
from langgraph.graph import StateGraph, START, END
from graph.state import TarkaState
from agents.web_scout import web_scout_node

def build_graph():
    graph = StateGraph(TarkaState)
    graph.add_node("web_scout", web_scout_node)
    graph.add_edge(START, "web_scout")
    graph.add_edge("web_scout", END)
    return graph.compile()
```

#### D. Test Run — `backend/main.py`

```python
from graph.graph import build_graph

graph = build_graph()
result = graph.invoke({"query": "Can LLMs reason?", "web_results": []})

for item in result["web_results"]:
    print(f"[{item['date']}] {item['title']}")
    print(f"  {item['claim'][:200]}")
    print(f"  {item['url']}\n")
```

### Milestone
Graph compiles and runs. Query goes in, five structured web results come out. The state contract is locked — every future node builds on top of it.

### What's Next (Day 2)
Add the `paper_scout_node` using the `arxiv` package. Extend `TarkaState` with `paper_results`. By end of Day 2, you'll see web results and paper abstracts side by side for the same query — and you'll already spot disagreements manually. That's the setup for the Critic on Day 4.

## Tarka — Day 2: Paper Scout

### What Day 2 Is About

Day 1 gave us web results — blog posts, product announcements, opinion pieces. Useful, but they don't carry citations or empirical evidence. To find *real* contradictions, we need to compare what the web says against what peer-reviewed papers actually show.

Day 2 adds the Paper Scout node, which queries ArXiv and pulls back paper abstracts, authors, and publication years. By end of day, the same query returns both web results and paper findings side by side. You'll start seeing disagreements manually — that's the entire setup for the Critic on Day 4.

---

### One Problem Worth Noting

When you pass a conversational query like *"Can LLMs reason?"* directly to the ArXiv search client, it interprets "Can" as an author name and returns papers by authors literally named "Can". 

The fix is a lightweight query cleaner that strips stop-words before hitting the ArXiv endpoint:

```python
import re

STOP_WORDS = {"can", "what", "is", "are", "how", "do", "does", "the", "a", "an"}

def clean_query(query: str) -> str:
    words = re.sub(r'[^\w\s]', '', query.lower()).split()
    keywords = [w for w in words if w not in STOP_WORDS]
    return " ".join(keywords)
```

*"Can LLMs reason?"* → `"llms reason"` → ArXiv returns papers on LLM reasoning, not papers by an author named Can.

---

### What Was Built

#### State Update — `backend/graph/state.py`

Added `paper_results` to the shared state. Each paper carries title, authors, abstract summary, publication year, and ArXiv ID.



#### Paper Scout Node — `backend/agents/paper_scout.py`

Queries ArXiv, maps the response into the same clean shape we used for web results.

```python

search_query = clean_arxiv_query(user_query)
    
    search = arxiv.Search(
        query=search_query,
        max_results=5,
        sort_by=arxiv.SortCriterion.Relevance
    )
```

#### Graph Update — `backend/graph/graph.py`

Added `paper_scout` as a second node. Graph is now sequential: `START → web_scout → paper_scout → END`.

```python
def build_graph():
    graph = StateGraph(TarkaState)
    graph.add_node("web_scout", web_scout_node)
    graph.add_node("paper_scout", paper_scout_node)
    graph.add_edge(START, "web_scout")
    graph.add_edge("web_scout", "paper_scout")
    graph.add_edge("paper_scout", END)
    return graph.compile()
```

#### Test Run — `backend/main.py`

```python
from graph.graph import build_graph

graph = build_graph()
result = graph.invoke({
    "query": "Can LLMs reason?",
    "web_results": [],
    "paper_results": []
})

print("=== WEB ===")
for item in result["web_results"]:
    print(f"[{item['date']}] {item['title']}")
    print(f"  {item['claim'][:200]}\n")

print("=== PAPERS ===")
for paper in result["paper_results"]:
    print(f"[{paper['year']}] {paper['title']}")
    print(f"  {paper['authors']}")
    print(f"  {paper['summary'][:200]}\n")
```

---

### Milestone

Running the graph now returns web results and paper abstracts side by side for the same query. Data ingestion phase is complete.

| End-to-end pipeline latency (cold, no memory) | ~3.0s | — |

### What's Next (Day 3)

Add the Orchestrator node. Its job is to set a `needs_fetch` flag — first queries fetch from both scouts, follow-up questions skip the network calls entirely and use existing results. That's what makes multi-turn conversation efficient without burning API credits.

## Tarka — Day 3: Orchestrator + Conditional Routing

### What Day 3 Is About

A linear pipeline is fine when every query needs fresh data. But in a multi-turn conversation, re-running both scouts for a follow-up question wastes ~3 seconds and burns API credits for no reason. The data is already in state.

Day 3 fixes this by adding an Orchestrator node that checks whether we actually need to fetch, and conditional edges that route the graph based on that decision.

---

### How Conditional Routing Works in LangGraph

Normal edges are fixed: A → B, always. Conditional edges say: *after this node, look at the state and decide where to go next.*

```python
graph.add_conditional_edges(
    "orchestrator",
    routing_function,           # reads state, returns a string
    {
        "fetch": "web_scout",   # if routing_function returns "fetch"
        "skip": "synthesizer"   # if routing_function returns "skip"
    }
)
```

The routing function doesn't call the next node directly — it just returns a string key. LangGraph maps that key to the next node. The nodes themselves stay decoupled.

---

### What Was Built

#### State Update — `backend/graph/state.py`

Two new fields. `needs_fetch` controls routing. `conversation_history` is planted now and used properly on Day 6.

```python
from typing import TypedDict, List, Dict, Any

class TarkaState(TypedDict):
    query: str
    web_results: List[Dict[str, Any]]
    paper_results: List[Dict[str, Any]]
    needs_fetch: bool
    conversation_history: List[Dict]
```

#### Orchestrator Node — `backend/agents/orchestrator.py`

Simple rule for now: empty conversation history means fresh query, fetch. Non-empty means follow-up, skip.

```python
from graph.state import TarkaState

def orchestrator_node(state: TarkaState) -> dict:
    is_followup = len(state.get("conversation_history", [])) > 0
    return {"needs_fetch": not is_followup}
```

#### Routing Function + Graph Update — `backend/graph/graph.py`

```python
from langgraph.graph import StateGraph, START, END
from graph.state import TarkaState
from agents.orchestrator import orchestrator_node
from agents.web_scout import web_scout_node
from agents.paper_scout import paper_scout_node

def route_after_orchestrator(state: TarkaState) -> str:
    return "fetch" if state["needs_fetch"] else "skip"

def build_graph():
    graph = StateGraph(TarkaState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("web_scout", web_scout_node)
    graph.add_node("paper_scout", paper_scout_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "fetch": "web_scout",
            "skip": END
        }
    )
    graph.add_edge("web_scout", "paper_scout")
    graph.add_edge("paper_scout", END)

    return graph.compile()
```

---

### The Routing Map

START
↓
Orchestrator
├── needs_fetch=True  → Web Scout → Paper Scout → END
└── needs_fetch=False → END (existing results preserved in state)

---

### Milestone

**Fresh query (~3010ms):** Orchestrator sets `needs_fetch=True`, both scouts run, results populate state.

**Follow-up (~7ms):** Orchestrator sets `needs_fetch=False`, scouts are bypassed entirely, existing results pass through untouched.

That 7ms number is the baseline for the memory layer story on Day 6.

### What's Next (Day 4)

The Critic node — the hardest day. It receives both scouts' outputs and cross-examines them for contradictions and consensus. The challenge isn't the structure, it's the prompt: getting an LLM to flag real contradictions without hallucinating ones that don't exist.

# Tarka — Day 4: Critic Node

## What Day 4 Is About

The Critic is Tarka's core value proposition. Everything before this — the scouts, the orchestrator, the routing — was plumbing. This is the node that actually does the thing Tarka promises: find where the web and academic literature disagree.

The goal is straightforward. Take web results and paper abstracts, cross-examine them, and return two structured lists — consensus points where both sources agree, and contradictions where they don't.

Getting there took most of Day 4.

---

## What Didn't Work (And Why)

The first approach used LangChain's `with_structured_output()` bound to a Pydantic schema (`CriticAnalysis` with nested `ConsensusModel` and `ContradictionModel` lists). The model consistently returned empty lists despite having good data.

The root cause was a competition between the `overall_summary` field and the structured lists. The model would do all its analytical reasoning inside the summary, then treat the structured fields as optional extras and leave them empty. Moving `overall_summary` to last in the schema, removing it entirely, splitting into two separate API calls, adjusting temperature from 0.0 to 0.7 — none of it reliably fixed the problem.

The structured output approach was abandoned. `with_structured_output()` is unreliable for complex nested schemas when the model has competing reasoning tasks in the same call.

---

## What Works: XML Generation + Regex Parsing

Instead of asking the model to return structured JSON, ask it to generate XML tags and parse those tags with regex. Two steps:

**Pass 1 — Generation:** Send a prompt asking the model to wrap its findings in explicit XML tags (`<consensus_point>`, `<contradiction_point>`, `<summary>`). Plain text generation, no schema enforcement.

**Pass 2 — Parsing:** Extract blocks with `re.findall`, pull individual fields with `re.search`. If a field is missing, default to `"N/A"`. No validation errors, no empty list failures.

This is more robust than `with_structured_output` for this use case because the model generates freely and the structure is imposed afterwards by the parser, not enforced during generation.

---

## The Prompt

The prompt that works gives the model a required XML structure and a small set of clear rules:

```python
system_instruction = (
    "You are an adversarial expert research evaluator cross-examining public claims against peer-reviewed evidence.\n"
    "Your objective is to thoroughly analyze the raw text blocks and output your findings using STRICT XML tags.\n\n"
    "RULES:\n"
    "1. Do NOT use Markdown formatting. Do NOT include conversational filler.\n"
    "2. Only output the requested tags and their contents.\n"
    "3. If you find no consensus or no contradictions, simply omit those specific tags.\n"
    "4. Output 'N/A' for any missing URLs or Paper IDs.\n\n"
    "REQUIRED STRUCTURE:\n"
    "<analysis>\n"
    "  <summary>2-3 sentence overview of the general trend.</summary>\n"
    "  <consensus_point>\n"
    "    <point>Core concept where both sources align</point>\n"
    "    <web_quote>Snippet from web</web_quote>\n"
    "    <source_url>URL</source_url>\n"
    "    <paper_quote>Snippet from paper</paper_quote>\n"
    "    <source_paper_id>Paper ID</source_paper_id>\n"
    "  </consensus_point>\n"
    "  <contradiction_point>\n"
    "    <conflict_topic>Specific focus of disagreement</conflict_topic>\n"
    "    <web_claim>Web's stance</web_claim>\n"
    "    <web_quote>Snippet from web</web_quote>\n"
    "    <source_url>URL</source_url>\n"
    "    <paper_claim>Paper's opposing stance</paper_claim>\n"
    "    <paper_quote>Snippet from paper</paper_quote>\n"
    "    <source_paper_id>Paper ID</source_paper_id>\n"
    "  </contradiction_point>\n"
    "</analysis>"
)
```

Key decisions:
- Temperature 0.3 — low enough for analytical consistency, not so low the model refuses to commit
- Claude Haiku 4.5 — fast and cheap for this generation task, quality holds up
- SystemMessage + HumanMessage split — role and rules in system, data in human

---

## What Was Built

#### Critic Node — `backend/agents/critic_two_pass.py`

```python
import re
from langchain_anthropic import ChatAnthropic
from graph.state import TarkaState
from langchain_core.messages import SystemMessage, HumanMessage

base_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3)

def extract_tag(text: str, tag: str) -> str:
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

def critic_two_pass_node(state: TarkaState) -> dict:
    user_query = state["query"]
    web_data = state.get("web_results", [])
    paper_data = state.get("paper_results", [])

    messages = [
        SystemMessage(content=system_instruction),  # full prompt as above
        HumanMessage(content=(
            f"Target Question: '{user_query}'\n\n"
            f"--- WEB SOURCES ---\n{web_data}\n\n"
            f"--- ACADEMIC PAPERS ---\n{paper_data}\n\n"
            "Generate the tag-based analysis now."
        ))
    ]

    raw_xml = base_llm.invoke(messages).content
    clean_xml = raw_xml.replace("```xml", "").replace("```", "").strip()

    overall_summary = extract_tag(clean_xml, "summary")

    consensus_list = []
    for block in re.findall(r"<consensus_point>(.*?)</consensus_point>", clean_xml, re.DOTALL):
        consensus_list.append({
            "point": extract_tag(block, "point"),
            "web_quote": extract_tag(block, "web_quote"),
            "paper_quote": extract_tag(block, "paper_quote"),
            "source_url": extract_tag(block, "source_url"),
            "source_paper_id": extract_tag(block, "source_paper_id")
        })

    contradiction_list = []
    for block in re.findall(r"<contradiction_point>(.*?)</contradiction_point>", clean_xml, re.DOTALL):
        contradiction_list.append({
            "conflict_topic": extract_tag(block, "conflict_topic"),
            "web_claim": extract_tag(block, "web_claim"),
            "web_quote": extract_tag(block, "web_quote"),
            "source_url": extract_tag(block, "source_url"),
            "paper_claim": extract_tag(block, "paper_claim"),
            "paper_quote": extract_tag(block, "paper_quote"),
            "source_paper_id": extract_tag(block, "source_paper_id")
        })

    return {
        "overall_summary": overall_summary,
        "consensus": consensus_list,
        "contradictions": contradiction_list
    }
```

#### Graph Update — `backend/graph/graph.py`

Replace `critic_node` import with `critic_two_pass_node`. No other graph changes needed.

---

## Sample Output

**Query:** *"blue light blocking glasses prevent digital eye strain"*

**Summary:** Web sources and academic literature show strong consensus that blue light blocking glasses lack scientific evidence for preventing digital eye strain. The primary causes of digital eye strain are ergonomic and behavioral rather than light-based.

**Consensus (3 points):** Digital eye strain caused by ergonomics not blue light; no evidence of ocular damage at normal screen exposure; blue light glasses don't improve sleep quality.

**Contradiction (1 point):** Mainstream sources say blue light glasses don't work, but one systematic review found blocking short-wavelength blue light specifically *did* reduce visual discomfort — a narrower, more precise finding than the broad web claim.

---

## Honest Notes

- `with_structured_output()` bound to nested Pydantic schemas is unreliable when the model has competing reasoning tasks. XML + regex is more robust for this pattern.
- The Critic sees contradictions before it writes them — the `overall_summary` accurately describes findings that the structured fields sometimes fail to capture. This is a known LLM behaviour with structured output constraints.
- Input capped at 5 web + 5 paper results. Higher counts (10+10) flood the context and cause empty outputs.
- OpenAlex occasionally times out. The fallback returns empty paper results and the Critic flags low confidence in the summary.

## What's Next (Day 5)

Synthesizer node — takes the full state (query + web results + paper results + critic output) and packages it into a clean final JSON object ready for the API and frontend to consume.

# Tarka — Day 5: Synthesizer Node

## What Day 5 Is About

Days 1-4 built the pipeline. The Synthesizer is the last node before data leaves the backend — it takes the full graph state and packages it into one clean JSON object ready for the API and frontend to consume.

Everything upstream produces raw, intermediate output. Web results are unsorted snippets. Paper results are abstract dumps. Critic output is a list of extracted blocks. The Synthesizer's job is to reorganise all of it, enrich it with suggested follow-ups, and produce a single payload that the UI can render directly without any further processing.

It's the shortest day in the pipeline. The hard reasoning happened in the Critic. The Synthesizer mostly structures and enriches.

---

## What the Synthesizer Adds

One thing the earlier nodes don't produce: **suggested follow-ups**. The Synthesizer reads the critic output and generates 2-3 natural follow-up questions the user might want to ask next. This is what makes the UI feel like a research assistant rather than a search engine — the system reasons about its own output and surfaces the next logical questions.

---

## Output Schema

```python
{
    "query": str,                    # cleaned/rephrased version of the input
    "summary": str,                  # overall trend across web and papers
    "consensus": List[dict],         # from Critic
    "contradictions": List[dict],    # from Critic
    "source_count": {                # how many sources were analysed
        "web": int,
        "papers": int
    },
    "suggested_followups": List[str] # 2-3 follow-up questions
}
```

---

## What Was Built

#### Synthesizer Node — `backend/agents/synthesizer.py`

Same XML + regex pattern as the Critic. One LLM call, structured output via tags, parsed deterministically.

```python
import re
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import TarkaState

synth_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3)

def extract_tag(text: str, tag: str) -> str:
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

def synthesizer_node(state: TarkaState) -> dict:
    query = state["query"]
    web_results = state.get("web_results", [])
    paper_results = state.get("paper_results", [])
    consensus = state.get("consensus", [])
    contradictions = state.get("contradictions", [])
    overall_summary = state.get("overall_summary", "")

    system_instruction = (
        "You are a research synthesis engine for a system called Tarka.\n"
        "You receive a research question, critic analysis results, and raw source data.\n"
        "Your job is to produce a final clean research package using STRICT XML tags.\n\n"
        "RULES:\n"
        "1. Do NOT use Markdown. Do NOT add conversational filler.\n"
        "2. Only output the requested XML tags.\n"
        "3. suggested_followups must be specific and grounded in the analysis — not generic questions.\n\n"
        "REQUIRED STRUCTURE:\n"
        "<synthesis>\n"
        "  <query>Rephrase the research question as a clean, neutral question</query>\n"
        "  <summary>2-3 sentences summarising the overall trend across web and papers</summary>\n"
        "  <followup>First specific follow-up question</followup>\n"
        "  <followup>Second specific follow-up question</followup>\n"
        "  <followup>Third specific follow-up question</followup>\n"
        "</synthesis>"
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=(
            f"Research Question: '{query}'\n\n"
            f"Overall Critic Summary: {overall_summary}\n\n"
            f"Consensus Points Found: {consensus}\n\n"
            f"Contradictions Found: {contradictions}\n\n"
            "Generate the synthesis package now."
        ))
    ]

    raw_xml = synth_llm.invoke(messages).content
    clean_xml = raw_xml.replace("```xml", "").replace("```", "").strip()

    followups = re.findall(
        r"<followup>(.*?)</followup>",
        clean_xml,
        re.DOTALL | re.IGNORECASE
    )

    final_payload = {
        "query": extract_tag(clean_xml, "query"),
        "summary": extract_tag(clean_xml, "summary"),
        "consensus": consensus,
        "contradictions": contradictions,
        "source_count": {
            "web": len(web_results),
            "papers": len(paper_results)
        },
        "suggested_followups": [f.strip() for f in followups]
    }

    print("[DEBUG - SYNTHESIZER] Final UI-ready JSON package compiled successfully.")
    return {"synthesis": final_payload}
```

#### State Update — `backend/graph/state.py`

Add `synthesis` to `TarkaState`:

```python
synthesis: dict
```

And initialise it in `main.py`:

```python
"synthesis": {}
```

#### Graph Update — `backend/graph/graph.py`

```python
from agents.synthesizer import synthesizer_node

builder.add_node("synthesizer", synthesizer_node)
builder.add_edge("critic", "synthesizer")
builder.add_edge("synthesizer", END)
```

---

## Sample Output

**Query:** *"blue light blocking glasses prevent digital eye strain from computer screens"*

```json
{
  "query": "Do blue light blocking glasses prevent digital eye strain from computer screens?",
  "summary": "Web sources and major health authorities show clear consensus that blue light glasses lack scientific evidence for preventing eye strain. Academic papers confirm this, noting strain stems from ergonomics and screen usage patterns — though one scoping review identifies limited evidence that blocking short-wavelength blue light may reduce visual discomfort.",
  "consensus": [
    {
      "point": "Digital eye strain is primarily caused by screen usage patterns and ergonomics, not blue light",
      "web_quote": "The best way to avoid eye strain is to take breaks from the screen frequently.",
      "paper_quote": "Management options for DES include following correct ergonomics like reducing average daily screen time, frequent blinking, improving lighting..."
    }
  ],
  "contradictions": [
    {
      "conflict_topic": "Efficacy of blue light blocking glasses for reducing digital eye strain",
      "web_claim": "Blue light glasses do not prevent eye strain and lack scientific evidence",
      "paper_claim": "One scoping review found that blocking short-wavelength blue light reduced visual discomfort in the studies examined"
    }
  ],
  "source_count": {"web": 7, "papers": 7},
  "suggested_followups": [
    "What methodological limitations were present in the scoping review that found blue light blocking reduced visual discomfort?",
    "Are there subgroups of users for whom blue light blocking glasses show measurable benefits despite the overall null findings?",
    "How do the mechanisms proposed by blue light blocking advocates differ from the actual mechanisms driving digital eye strain?"
  ]
}
```

---

## Honest Notes

- The Synthesizer rephrases the input query into a clean question. This is intentional — it normalises inconsistent user input before it hits the UI.
- Suggested follow-ups are grounded in the critic output, not generated generically. If the critic finds no contradictions, the follow-ups reflect that and ask clarifying questions instead.
- The `synthesis` dict is what the FastAPI endpoint will serve directly. Everything else in state is intermediate.

---

## Pipeline Complete

Days 1-5 represent the full core pipeline:

```
Query
  → Orchestrator (routing)
  → Web Scout (Tavily)
  → Paper Scout (OpenAlex)
  → Critic (XML + regex, contradiction detection)
  → Synthesizer (final JSON package)
```

Input: a research question.
Output: structured consensus, contradictions, sources, and suggested follow-ups.

## What's Next (Day 6)

Memory layer — `conversation_history` is already in state, planted on Day 3. Day 6 wires it up properly so follow-up queries use existing synthesis context without re-fetching from scouts.

# Tarka — Day 7: FastAPI Backend + SSE Streaming

## What Day 7 Is About

Days 1-5 built the pipeline. Day 7 puts it behind a real HTTP server so anything — a browser, a React frontend, Postman — can talk to it.

Two things happen here. First, the LangGraph pipeline is exposed as a POST endpoint. Second, instead of waiting for the full pipeline to complete before responding, the server streams live status updates back to the client as each node finishes. The client knows the orchestrator is done before the web scout even starts.

That streaming behaviour is what makes Tarka feel alive rather than frozen for 20 seconds.

---

## SSE vs WebSockets

Server-Sent Events (SSE) is the right choice here because the communication is one-directional — server pushes updates to client, client never pushes back mid-stream. SSE is simpler than WebSockets for this pattern: no handshake protocol, native browser support via `EventSource`, and FastAPI handles it with a single `StreamingResponse`.

The tradeoff: SSE doesn't support POST requests natively in the browser's `EventSource` API. The React frontend will use `fetch` with `ReadableStream` instead — covered on Day 8.

---

## What Was Built

#### Server — `backend/server.py`

```python
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

from graph.graph import build_graph

app = FastAPI(title="Tarka Research API")
graph = build_graph()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str
    conversation_history: List[Dict[str, Any]] = []

async def run_research_stream(request: ResearchRequest):
    initial_state = {
        "query": request.query,
        "web_results": [],
        "paper_results": [],
        "conversation_history": request.conversation_history,
        "needs_fetch": False,
        "consensus": [],
        "contradictions": [],
        "overall_summary": "",
        "synthesis": {}
    }

    try:
        async for step in graph.astream(initial_state):
            for node_name, node_update in step.items():

                status_message = {
                    "type": "status",
                    "node": node_name,
                    "message": f"Executing {node_name.replace('_', ' ')}..."
                }
                yield f"data: {json.dumps(status_message)}\n\n"

                if node_name == "synthesizer" and "synthesis" in node_update:
                    result_message = {
                        "type": "result",
                        "payload": node_update["synthesis"]
                    }
                    yield f"data: {json.dumps(result_message)}\n\n"

                await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@app.post("/api/research")
async def research_endpoint(request: ResearchRequest):
    print(f"Received: {request.query}")
    return StreamingResponse(
        run_research_stream(request),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Three Design Decisions Worth Knowing

**`graph.astream()` not `graph.invoke()`**
`invoke()` blocks until the full pipeline completes. `astream()` yields a dict after every node — `{"node_name": state_update}` — which is what lets us push live status events. Without this, the client would get nothing for 20 seconds then everything at once.

**Two event types**
Every node fires a `status` event. Only the Synthesizer fires a `result` event. The frontend ignores status events for data rendering but uses them to animate a progress indicator.

**CORS origin**
Currently set to `http://localhost:5173` — Vite's default dev port. Don't set it to `*` in production.

---

## Verified in Postman

SSE events arrive in reverse chronological order in Postman's response panel (newest at top):

```
{"type": "done"}
{"type": "result", "payload": {"query": "Can LLMs reason cognitively?", "summary": "...", ...}}
{"type": "status", "node": "synthesizer", "message": "Executing synthesizer..."}
{"type": "status", "node": "critic", "message": "Executing critic..."}
{"type": "status", "node": "paper_scout", "message": "Executing paper scout..."}
{"type": "status", "node": "web_scout", "message": "Executing web scout..."}
{"type": "status", "node": "orchestrator", "message": "Executing orchestrator..."}
```

200 OK, 23.27s end-to-end, 4.25KB payload. Pipeline latency is dominated by the two LLM calls — Critic and Synthesizer.

---

## One Fix to Make Before Day 8

The CORS `allow_origins` in the uploaded file is set to `http://localhost:8000` — that's the backend's own port, not the frontend's. Change it to `http://localhost:5173` before wiring up React or every frontend request will be blocked.

---

## Honest Notes

- `reload=True` in uvicorn means the server restarts on every file save. Turn it off if you notice the graph being rebuilt mid-request during testing.
- The `await asyncio.sleep(0.1)` between events ensures the stream flushes cleanly to the client. Without it, events can batch and arrive together.
- Error handling currently surfaces the raw exception message to the client. Fine for dev, should be sanitised before any public deployment.

---

## What's Next (Day 8)

React frontend — consuming the SSE stream via `fetch` + `ReadableStream`, rendering consensus and contradiction cards, animating the status bar as each node fires.

# Tarka — Day 8: React Frontend

## What Day 8 Is About

The backend has been working since Day 7 — a FastAPI server streaming SSE events as the pipeline runs. Day 8 puts a face on it. The goal is a clean, minimal UI that gets out of the way and lets the research output speak.

One design principle drove every decision: the user came here frustrated with contradictory Google results. They want clarity, not more noise. The interface should feel like a research assistant that already did the reading.

---

## Two States, One Page

The app lives in two visual states:

**Landing** — Tarka centered on the page, tagline, search bar. Nothing else.

**Results** — Search bar slides to the top, pipeline status appears line by line as nodes fire, synthesis renders below once complete.

The transition between states is controlled by a single boolean — `!!synthesis || loading` — passed as `hasResults` to `SearchBar`. No routing, no page changes. One component that knows which state it's in.

---

## Component Decisions

**`SearchBar`**
Owns the input and submit logic. Two visual modes controlled by `hasResults` — centered hero layout on landing, compact top bar on results. The slide happens via CSS transition on `minHeight` and `padding`. The logo appears inline at the top once results show so the user always knows what they're using.

**`StatusBar`**
Receives the `status` array from App state which grows as SSE events arrive. Latest message is full opacity with a green dot, all previous messages fade to 40%. Gives the feel of a live process without being noisy. Hidden once synthesis arrives.

**`SynthesisPanel`**
The main output surface. Three sections:
- Overview card — summary text plus source count (web · papers)
- Consensus cards — green left border, web quote and paper quote side by side with source links
- Contradiction cards — red border, two-column layout with web claim on the left and paper claim on the right. This is the visual moment that makes Tarka different from a search engine.

**`FollowUpChips`**
Horizontally wrapping pill buttons at the bottom. Each chip sends its text back through `onSearch` — the same handler as the main search bar. Hover state shifts border and text color to draw attention without being loud.

---

## SSE Consumption

The browser's native `EventSource` API doesn't support POST requests. Instead, `fetch` with `ReadableStream` is used — the response body is read chunk by chunk, decoded, split on newlines, and parsed as JSON events.

Three event types arrive from the backend:
- `status` — appended to the status array, triggers StatusBar update
- `result` — sets synthesis state, triggers SynthesisPanel render
- `done` — sets loading to false

---

## Theme System

One `data-theme` attribute on `document.documentElement`, toggled by a button in the top right. All colors are CSS variables — `--bg-primary`, `--card-bg`, `--consensus-bg`, `--contradiction-border` etc. — defined in `index.css` for both dark and light values. Components use inline `style` props referencing these variables. No Tailwind for colors — CSS variables give instant theme switching without a re-render.

Dark is the default. The toggle sits top-right, stays fixed across both states.

---

## What the Finished UI Looks Like

Landing page — Tarka centered, tagline, search bar, dark background. Clean enough that the first impression is the product, not the chrome.

Results page — search bar at top with query still visible, node status messages appearing one by one (orchestrator → web scout → paper scout → critic → synthesizer), then synthesis fading in below. Overview summary, consensus cards in green, contradiction card in red two-column layout, follow-up chips at the bottom.

---

## Honest Notes

- The search bar slide animation uses `minHeight` transitioning from `100vh` to `65px` — `auto` didn't animate reliably in the flex container, `65px` is the pragmatic fix.
- Follow-up chips currently re-trigger the full pipeline including scouts. Memory-based skip logic (Orchestrator `needs_fetch=False`) was temporarily disabled because previous results weren't being passed forward — addressed in Day 9.
- No loading skeleton or error boundary yet — both are Day 9 items.
- CORS origin must be exactly `http://localhost:5173` with no trailing slash — an exact string match in FastAPI middleware.

---

## What's Next (Day 9)

Error handling, resilience passes, follow-up memory properly wired, and polish. The system works end-to-end — Day 9 makes it robust.

# Tarka — Day 9: Resilience, Follow-up Memory & Polish

## What Day 9 Is About

Day 8 left a working system. Day 9 makes it robust — handling failures gracefully, wiring up follow-up memory properly, and fixing the small UX gaps that make the difference between a demo that feels rough and one that feels considered.

---

## Error Handling

### Frontend

Three failure cases handled:

**Backend unreachable** — `fetch` throws when the server isn't running. Caught in the try/catch wrapping `handleSearch`, displays a red error card: *"Backend unreachable. Make sure the server is running on port 8000."*

**Stream error event** — if the backend sends `{"type": "error", "message": "..."}` mid-stream, the frontend catches it, sets error state, and stops loading. The same red card renders with the server's message.

**Malformed SSE line** — individual lines that fail `JSON.parse` are silently skipped with `continue`. The stream continues processing remaining lines rather than crashing.

**Empty synthesis** — when both consensus and contradictions arrays are empty, `SynthesisPanel` renders a neutral message: *"No consensus or contradictions found for this query. Try a more contested topic."* instead of a blank page.

### Backend

**Tavily failure** — `web_scout_node` wraps the API call in try/catch. On failure, returns `{"web_results": []}` and logs the error. Pipeline continues with papers only.

**OpenAlex/Semantic Scholar timeout** — `paper_scout_node` already returns `{"paper_results": []}` on exception. Pipeline continues with web only.

**Critic guard** — if either `web_data` or `paper_data` is empty, the Critic skips LLM analysis entirely and returns `"Academic sources unavailable. Analysis requires both web and paper data."` This prevents hallucinated contradictions from running on partial data.

**Critic malformed XML** — the regex parse step is wrapped in try/catch. On failure, returns empty consensus and contradictions with a failure summary rather than crashing the pipeline.

---

## Follow-up Memory

### The Problem

When a follow-up chip is clicked, the Orchestrator correctly skips the scouts — no need to re-fetch for the same topic. But the previous web and paper results weren't being passed forward, so the Critic received empty data and the guard fired every time.

### The Fix

Three-part change:

**Synthesizer** includes raw `web_results` and `paper_results` in `final_payload` alongside the processed output. This gives the frontend access to the data it needs to pass forward.

**Frontend** stores `lastResults` in state when each result arrives. Every subsequent request sends `previous_web_results` and `previous_paper_results` in the request body. Conversation history is kept lean — just the summary string per turn, not the full payload — to avoid bloating the LLM context.

**Orchestrator** sets `needs_fetch: False` explicitly when `conversation_history` is non-empty. Scouts are bypassed, previous results flow directly into the Critic with the new question.

### Result

- Fresh query → full pipeline (~20-25s)
- Follow-up click → scouts skipped, Critic + Synthesizer only (~8-12s)
- New synthesis generated in context of previous findings

---

## UX Polish

**Search bar updates on follow-up** — `SearchBar` accepts a `value` prop and syncs local input state via `useEffect`. When a chip is clicked, `query` state in App updates, which flows down as `value` and updates the visible input.

**Auto-scroll to synthesis** — a `useRef` attached to the `SynthesisPanel` wrapper triggers `scrollIntoView({ behavior: "smooth" })` when synthesis state changes from null to populated. User doesn't have to scroll manually after a 20-second wait.

**Hero collapses on search trigger** — `hasResults` prop now receives `!!synthesis || loading` instead of just `!!synthesis`. The landing hero disappears and the search bar slides to the top the moment search is triggered, not after synthesis arrives.

---

## Honest Notes

- Follow-up memory is session-scoped — refreshing the page resets everything. Persistent memory across sessions is a future feature.
- Conversation history grows unboundedly within a session. For long sessions with many follow-ups this could degrade synthesis quality. A simple fix would be keeping only the last 2-3 turns — not implemented yet.
- Mobile layout not tested. At narrow viewports the contradiction two-column layout likely breaks — noted as a known limitation.
- Rate limiting not implemented. Rapid follow-up clicks can queue multiple pipeline runs simultaneously. Acceptable for a portfolio demo, not for production.

---

## What's Next (Day 10)

README metrics filled in, Mermaid architecture diagram finalised, Docker setup, and demo preparation — three curated queries that show Tarka at its best.