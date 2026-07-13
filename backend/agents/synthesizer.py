from pydantic import BaseModel, Field
from typing import List, Dict
from langchain_anthropic import ChatAnthropic
from graph.state import TarkaState
from langchain_core.messages import SystemMessage, HumanMessage

# --- SCHEMA DEFINITIONS FOR THE UI CONTRACT ---
class SourceCountModel(BaseModel):
    web: int = Field(description="Total number of web sources analyzed.")
    papers: int = Field(description="Total number of academic papers analyzed.")

class TarkaResponseSchema(BaseModel):
    query: str = Field(description="The original user query.")
    summary: str = Field(description="The verified overall summary from the Critic node.")
    consensus: List[dict] = Field(description="The list of consensus objects passed from the state.")
    contradictions: List[dict] = Field(description="The list of contradiction objects passed from the state.")
    source_count: SourceCountModel = Field(description="Breakdown of how many sources were integrated.")
    suggested_followups: List[str] = Field(default_factory=list, description="2-3 natural follow-up questions generated dynamically based on the specific contradictions and consensus found.")

# --- LLM INITIALIZATION ---
base_llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001", # type: ignore
    temperature=0.3
) # type: ignore
structured_synthesizer = base_llm.with_structured_output(TarkaResponseSchema) # type: ignore

# --- NODE IMPLEMENTATION ---
def synthesizer_node(state: TarkaState) -> dict:
    user_query = state["query"]
    web_data = state.get("web_results", [])
    paper_data = state.get("paper_results", [])
    critic_summary = state.get("overall_summary", "")
    consensus_list = state.get("consensus", [])
    contradiction_list = state.get("contradictions", [])
    
    # Calculate metadata metrics natively
    counts = {
        "web": len(web_data),
        "papers": len(paper_data)
    }

    system_instruction = (
        "You are a strict data packaging API for a research engine.\n"
        "Your sole task is to take pre-calculated research metrics and format them into the requested schema.\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. Map the consensus, contradictions, and summary data exactly as provided without changing their meaning or text.\n"
        "2. You MUST generate exactly 3 follow-up questions in 'suggested_followups'. This field is never optional.\n"
        "3. Follow-up questions must be specific to the actual findings — not generic. Reference specific claims, papers, or contradictions found in the data.\n"
        "4. If consensus and contradictions are both empty, generate follow-up questions that would help find better sources or reframe the query.\n"
    )

    human_payload = (
        f"Original Query: {user_query}\n\n"
        f"Overall Summary: {critic_summary}\n\n"
        f"Consensus Points: {consensus_list}\n\n"
        f"Contradiction Points: {contradiction_list}\n\n"
        f"Source Metrics: {counts}"
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=human_payload)
    ]

    # Map directly to the Pydantic UI schema
    final_output: TarkaResponseSchema = structured_synthesizer.invoke(messages) # type: ignore

    print("[DEBUG - SYNTHESIZER] Final UI-ready JSON package compiled successfully.")

    # Return the dictionary version to be stored in final_payload
    return {
        "final_payload": {
            **final_output.model_dump(),
            "web_results": web_data,
            "paper_results": paper_data
        }
    }