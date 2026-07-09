# backend/agents/orchestrator.py
from graph.state import TarkaState

def orchestrator_node(state: TarkaState) -> dict:
    is_followup = len(state.get("conversation_history", [])) > 0
    if is_followup:
        print("Orchestrator: Follow-up detected. Skipping scouts.")
        return {"needs_fetch": False}
    print("Orchestrator: Fresh query. Triggering fetch.")
    return {"needs_fetch": True}