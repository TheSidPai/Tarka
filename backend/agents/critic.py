# backend/agents/critic.py
from pydantic import BaseModel, Field
from typing import List
from langchain_anthropic import ChatAnthropic
from graph.state import TarkaState
from langchain_core.messages import SystemMessage, HumanMessage

# class ConsensusModel(BaseModel):
#     point: str = Field(description="The core concept where both sources align.")
#     web_quote: str = Field(description="A relevant phrase from the web. Partial matches or slight paraphrasing are completely acceptable.")
#     paper_quote: str = Field(description="A relevant phrase from the paper. Partial matches or slight paraphrasing are completely acceptable.")
#     source_url: str = Field(default="N/A", description="Just output 'N/A' if no URL is visible.")
#     source_paper_id: str = Field(default="N/A", description="Just output 'N/A' if no ID is visible.")

# class ContradictionModel(BaseModel):
#     conflict_topic: str = Field(description="The specific focus of the disagreement (e.g., 'AGI Status').")
#     web_claim: str = Field(description="A short summary of the web's stance.")
#     web_quote: str = Field(description="A relevant phrase from the web. Partial matches or slight paraphrasing are completely acceptable.")
#     source_url: str = Field(default="N/A", description="Just output 'N/A' if no URL is visible.")
#     paper_claim: str = Field(description="A short summary of the paper's stance.")
#     paper_quote: str = Field(description="A relevant phrase from the paper. Partial matches or slight paraphrasing are completely acceptable.")
#     source_paper_id: str = Field(default="N/A", description="Just output 'N/A' if no ID is visible.")

class ConsensusModel(BaseModel):
    point: str = Field(description="The core concept where both sources align.")
    web_quote: str = Field(description="Relevant phrase from the web.")
    paper_quote: str = Field(description="Relevant phrase from the paper.")

class ContradictionModel(BaseModel):
    conflict_topic: str = Field(description="The exact topic of disagreement.")
    web_claim: str = Field(description="The web's stance or assertion.")
    paper_claim: str = Field(description="The paper's opposing stance.")


# The master container envelope required by the LLM output engine
# class CriticAnalysis(BaseModel):
#     consensus: List[ConsensusModel] = Field(default_factory=list, description="List of all verified points of alignment across both data sets.")
#     contradictions: List[ContradictionModel] = Field(default_factory=list, description="List of all verified structural contradictions across both data sets.")
#     overall_summary: str = Field(default_factory=str, description="Written AFTER populating consensus and contradictions. 2-3 sentences covering how many sources were analysed and the general trend.")

# The master container envelope required by the LLM output engine
class CriticAnalysis(BaseModel):
    # MOVE SUMMARY TO THE TOP: Forces Chain-of-Thought reasoning first
    overall_summary: str = Field(description="Write this FIRST. Summarize the general trend and state exactly how many contradictions or consensus points you found.")
    
    # Add aggressive MANDATORY tags to the list descriptions
    consensus: List[ConsensusModel] = Field(default_factory=list, description="MANDATORY if consensus exists. You must populate this list with the exact data to prove your summary.")
    contradictions: List[ContradictionModel] = Field(default_factory=list, description="MANDATORY if contradictions exist. You must populate this list with the exact data to prove your summary.")

# Schema 1 — consensus only
class ConsensusAnalysis(BaseModel):
    consensus: List[ConsensusModel] = Field(default_factory=list, description="List of all verified points of alignment across both data sets.")

# Schema 2 — contradictions only
class ContradictionAnalysis(BaseModel):
    contradictions: List[ContradictionModel] = Field(default_factory=list, description="List of all verified structural contradictions across both data sets.")

# Initialize Claude with your active API credentials
# It automatically reads ANTHROPIC_API_KEY from os.environ
temp = 0.3
critic_llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    temperature=temp # Low temperature guarantees rigid analytical deduction with zero creative fluff
) # type: ignore

print(f"Temperature: {temp}")

# Two focused LLMs
consensus_critic = critic_llm.with_structured_output(ConsensusAnalysis) #type: ignore
contradiction_critic = critic_llm.with_structured_output(ContradictionAnalysis) #type: ignore

# Bind our schema contract directly to the inference model
structured_critic = critic_llm.with_structured_output(CriticAnalysis) #type: ignore

def critic_node(state: TarkaState) -> dict:
    user_query = state["query"]
    web_data = state.get("web_results", [])
    paper_data = state.get("paper_results", [])
    
    messages = [
        SystemMessage(content=(
            "You are an adversarial expert research evaluator analyzing data for a research engine named Tarka.\n"
            "Your goal is to cross-examine high-level claims from the open web against dense empirical findings from academic papers.\n\n"
            "EVALUATION DIRECTIVES:\n"
            "1. Write the 'overall_summary' FIRST to think through the relationship and declare how many connections you found.\n"
            "2. Identify 'contradictions' where there is conceptual friction, competing definitions, or direct disagreements.\n"
            "3. Identify 'consensus' where an academic paper's findings, benchmarks, or goals validate or support a web claim.\n"
            "4. ASYMMETRY RULE: Web results are naturally brief snippets. Treat them as representative arguments. Do not penalize them for lacking deep academic syntax. If a web claim is too vague to test, skip it.\n"
            "5. EXTRACT THE PROOF: You MUST populate the 'consensus' and 'contradictions' lists if you mentioned them in your summary. Extract the closest corresponding sentences into 'web_quote' and 'paper_quote'.\n"
        )),
        HumanMessage(content=(
            f"Target Research Question: '{user_query}'\n\n"
            "--- INGESTED SURFACE WEB CLAIMS ---\n"
            f"{web_data}\n\n"
            "--- INGESTED ACADEMIC PAPERS ---\n"
            f"{paper_data}\n\n"
            "Find all consensus points and contradictions between these sources."
        ))
    ]
    
    # Trigger a single model evaluation using the master schema
    analysis_payload: CriticAnalysis = structured_critic.invoke(messages) # type: ignore

    print("\n[DEBUG - UNIFIED] Output payload generated successfully.")

    return {
        "overall_summary": analysis_payload.overall_summary,
        "consensus": [item.model_dump() for item in analysis_payload.consensus],
        "contradictions": [item.model_dump() for item in analysis_payload.contradictions]
    }

def critic_node_split(state: TarkaState) -> dict:
    user_query = state["query"]
    web_data = state.get("web_results", [])
    paper_data = state.get("paper_results", [])
    
    # --- PROMPT 1: STRICTLY CONSENSUS ---
    consensus_messages = [
        SystemMessage(content=(
            "You are a research analyst for the Tarka engine. Your SOLE task is to find points of AGREEMENT (consensus) "
            "between high-level web claims and dense academic papers.\n\n"
            "EVALUATION DIRECTIVES:\n"
            "1. Identify 'consensus' where an academic paper's findings or goals validate a web claim.\n"
            "2. ASYMMETRY RULE: Web results are brief snippets. Treat them as representative arguments. Do not penalize them for lacking academic syntax.\n"
            "3. Ground your analysis by extracting the exact 'web_quote' and 'paper_quote'. If a web snippet is short, capture the text available.\n"
            "4. Look proactively for conceptual alignments. Do not invent fake data. If after analysis you find zero consensus despite having both web and paper data, "
            "that is almost certainly wrong. Re-examine and commit to your best analytical judgment by adding your findings.\n"
        )),
        HumanMessage(content=(
            f"Target Question: '{user_query}'\n\n"
            f"Web sources:\n{web_data}\n\n"
            f"Academic papers:\n{paper_data}\n\n"
            "Find all consensus points between these sources."
        ))
    ]

    # --- PROMPT 2: STRICTLY CONTRADICTIONS ---
    contradiction_messages = [
        SystemMessage(content=(
            "You are an adversarial research analyst for the Tarka engine. Your SOLE task is to find points of FRICTION (contradictions) "
            "between high-level web claims and dense academic papers.\n\n"
            "EVALUATION DIRECTIVES:\n"
            "1. Identify 'contradictions' where there is conceptual friction, competing definitions, or direct disagreements.\n"
            "2. ASYMMETRY RULE: Web results are brief snippets. Treat them as representative arguments. Do not penalize them for lacking academic syntax.\n"
            "3. Ground your analysis by extracting the exact 'web_quote' and 'paper_quote'. If a web snippet is short, capture the text available.\n"
            "4. Look proactively for conceptual clashes. Do not invent fake data. If after analysis you find zero contradictions despite having both web and paper data, "
            "that is almost certainly wrong. Re-examine and commit to your best analytical judgment by adding your findings.\n"
        )),
        HumanMessage(content=(
            f"Target Question: '{user_query}'\n\n"
            f"Web sources:\n{web_data}\n\n"
            f"Academic papers:\n{paper_data}\n\n"
            "Find all contradictions and points of tension between these sources."
        ))
    ]

    # Trigger both models independently
    consensus_result = consensus_critic.invoke(consensus_messages)
    contradiction_result = contradiction_critic.invoke(contradiction_messages)

    print("\n[DEBUG - SPLIT] Consensus and Contradiction payloads generated successfully.")

    return {
        "overall_summary": "Overall summary is bypassed in split-node execution.",
        "consensus": [item.model_dump() for item in consensus_result.consensus], # type: ignore
        "contradictions": [item.model_dump() for item in contradiction_result.contradictions] # type: ignore
    }