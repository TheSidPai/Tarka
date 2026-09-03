import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import time

# Import your graph builder
from graph.graph import build_graph

# Initialize the app and the LangGraph engine
app = FastAPI(title="Tarka Research API")
graph = build_graph()

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
    query: str
    conversation_history: List[Dict[str, Any]] = []
    previous_web_results: List[Dict[str, Any]] = []
    previous_paper_results: List[Dict[str, Any]] = []

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



# --- API ENDPOINT ---
@app.post("/api/research")
async def research_endpoint(request: ResearchRequest):
    """
    Returns a StreamingResponse that keeps the HTTP connection open 
    and pushes events as they happen.
    """
    print(f"Received research request: {request.query}")
    return StreamingResponse(
        run_research_stream(request), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    
    # Run the server on port 8000
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)