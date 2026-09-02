from pydantic import BaseModel, Field
from typing import List, Dict
from agents.llm import FallbackLLM
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

class FollowUpSchema(BaseModel):
    """The only thing the LLM actually generates here.

    Everything else in TarkaResponseSchema is already known to Python by the
    time this node runs, so asking the model to echo it back was pure risk:
    under a large consensus/contradiction payload it would silently omit
    required fields and the whole request died on a ValidationError. Same
    schema fatigue the Critic hit — the fix is the same, only ask the model
    for what it alone can produce.
    """
    suggested_followups: List[str] = Field(description="Exactly 3 follow-up questions.")

# --- LLM INITIALIZATION ---
# Anthropic primary, Gemini fallback — see agents/llm.py. The schema is bound
# to every provider in the chain, so a fallback returns the same type.
followup_generator = FallbackLLM(temperature=0.3, schema=FollowUpSchema)


def _fallback_followups(contradictions: list, consensus: list) -> List[str]:
    """Deterministic questions for when generation fails or returns nothing.

    The UI always renders chips, so it must never be handed an empty list.
    """
    questions = []
    for c in contradictions[:2]:
        topic = c.get("conflict_topic")
        if topic:
            questions.append(f"What explains the disagreement over {topic}?")
    for c in consensus[:2]:
        point = c.get("point")
        if point:
            questions.append(f"How strong is the evidence that {point[0].lower() + point[1:]}?")
    questions.extend([
        "Which sources are most credible on this question?",
        "What would stronger evidence on this look like?",
        "How has the evidence on this changed over time?",
    ])
    return questions[:3]

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
        "You generate follow-up research questions for a cross-examination engine.\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. You MUST generate exactly 3 questions.\n"
        "2. Questions must be specific to the actual findings — not generic. Reference specific claims, papers, or contradictions found in the data.\n"
        "3. If consensus and contradictions are both empty, generate questions that would help find better sources or reframe the query.\n"
    )

    human_payload = (
        f"Original Query: {user_query}\n\n"
        f"Overall Summary: {critic_summary}\n\n"
        f"Consensus Points: {consensus_list}\n\n"
        f"Contradiction Points: {contradiction_list}"
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=human_payload)
    ]

    # A failure here must not sink the request — every other field is already
    # in hand, so degrade to deterministic questions rather than raising.
    try:
        followups = followup_generator.invoke(messages).suggested_followups # type: ignore
    except Exception as e:
        print(f"[SYNTHESIZER] Follow-up generation failed: {type(e).__name__}: {e}")
        followups = []

    if not followups:
        followups = _fallback_followups(contradiction_list, consensus_list)

    # Assemble the UI contract in Python. The schema still validates the shape,
    # it just isn't the LLM's job to fill it in any more.
    final_output = TarkaResponseSchema(
        query=user_query,
        summary=critic_summary,
        consensus=consensus_list,
        contradictions=contradiction_list,
        source_count=SourceCountModel(**counts),
        suggested_followups=followups[:3],
    )

    print(f"[DEBUG - SYNTHESIZER] Packaged {len(consensus_list)} consensus, "
          f"{len(contradiction_list)} contradictions, {len(final_output.suggested_followups)} follow-ups.")

    # Return the dictionary version to be stored in final_payload
    return {
        "final_payload": {
            **final_output.model_dump(),
            "web_results": web_data,
            "paper_results": paper_data
        }
    }