from typing import TypedDict, List, Dict, Any

class TarkaState(TypedDict):
    query: str
    web_results: List[Dict[str, Any]]
    paper_results: List[Dict[str, Any]]
    # "ok" | "failed" | "empty" — separate keys because the scouts now run in
    # parallel, and two nodes writing one key needs a reducer.
    web_status: str
    paper_status: str
    needs_fetch: bool
    conversation_history: List[Dict]
    consensus: List[Dict[str, Any]] 
    contradictions: List[Dict[str, Any]]   
    overall_summary: str
    final_payload: Dict[str, Any]
    # An asyncio.Queue the server passes in so the Critic can push the summary
    # as it generates. Declared here because LangGraph drops state keys that
    # aren't channels. None in the headless harness and in tests.
    _partial_queue: Any