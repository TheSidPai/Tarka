from typing import TypedDict, List, Dict, Any

class TarkaState(TypedDict):
    query: str
    web_results: List[Dict[str, Any]]
    paper_results: List[Dict[str, Any]]
    needs_fetch: bool
    conversation_history: List[Dict]
    consensus: List[Dict[str, Any]] 
    contradictions: List[Dict[str, Any]]   
    overall_summary: str
    final_payload: Dict[str, Any]