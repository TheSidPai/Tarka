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
    # Initialize the required state 
    now = time.time()
    initial_state = {
        "query": request.query,
        "web_results": request.previous_web_results,
        "paper_results": request.previous_paper_results,
        "conversation_history": request.conversation_history,
        "needs_fetch": False,
        "consensus": [],
        "contradictions": [],
        "overall_summary": "",
        "final_payload": {}
    }

    try:
        # graph.astream() yields the state updates sequentially as nodes complete
        async for step in graph.astream(initial_state):
            # step is a dict like {"web_scout": {"web_results": [...]}}
            for node_name, node_update in step.items():
                
                # 1. Send a status update to the frontend UI. astream() yields a
                # step once the node has finished, so this is past tense — the
                # work is already done by the time the message goes out.
                status_message = {
                    "type": "status",
                    "node": node_name,
                    "message": f"{node_name.replace('_', ' ').capitalize()} complete"
                }
                yield f"data: {json.dumps(status_message)}\n\n"
                
                # 2. If the Synthesizer just finished, push the final UI payload!
                if node_name == "synthesizer" and "final_payload" in node_update:
                    result_message = {
                        "type": "result",
                        "payload": node_update["final_payload"]
                    }
                    yield f"data: {json.dumps(result_message)}\n\n"

                # Small sleep to ensure the stream flushes smoothly
                await asyncio.sleep(0.1)

        print("Time taken for research: {:.2f} seconds".format(time.time() - now))    
        # Tell the frontend to close the connection
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        error_message = {"type": "error", "message": str(e)}
        yield f"data: {json.dumps(error_message)}\n\n"



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