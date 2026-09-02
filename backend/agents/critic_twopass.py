import re
from agents.history import format_prior_findings
from agents.llm import FallbackLLM
from graph.state import TarkaState
from langchain_core.messages import SystemMessage, HumanMessage

# --- LLM INITIALIZATION ---
# Anthropic primary, Gemini fallback — see agents/llm.py.
base_llm = FallbackLLM(temperature=0.4)

# --- HELPER PARSER FUNCTION ---
def extract_tag(text: str, tag: str) -> str:
    """Safely extracts text between XML tags using Regex."""
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

def critic_two_pass_node(state: TarkaState) -> dict:
    user_query = state["query"]
    web_data = state.get("web_results", [])
    paper_data = state.get("paper_results", [])

    if not paper_data:
        print("[CRITIC] No paper data — skipping analysis to avoid hallucination.")
        return {
            "overall_summary": "Academic sources unavailable. Analysis requires both web and paper data.",
            "consensus": [],
            "contradictions": []
        }
    
    if not web_data:
        print("[CRITIC] No web data — skipping analysis to avoid hallucination.")
        return {
            "overall_summary": "Web sources unavailable. Analysis requires both web and paper data.",
            "consensus": [],
            "contradictions": []
        }
    
    # ------------------------------------------------------------------
    # PASS 1: GENERATION (Tag-Based Structuring)
    # ------------------------------------------------------------------
    system_instruction = (
        "You are an adversarial expert research evaluator cross-examining public claims against peer-reviewed evidence.\n"
        "Your objective is to thoroughly analyze the raw text blocks and output your findings using STRICT XML tags.\n\n"
        "RULES:\n"
        "1. Do NOT use Markdown formatting. Do NOT include conversational filler.\n"
        "2. Only output the requested tags and their contents.\n"
        "3. If you find no consensus or no contradictions, simply omit those specific tags.\n"
        "4. Output 'N/A' for any missing URLs or Paper IDs.\n"
        "5. An EARLIER IN THIS THREAD section may appear below. It is NOT evidence.\n"
        "   It records conclusions you already drew, not sources. Never quote it, cite\n"
        "   it, or treat any finding in it as established fact. EVERY quote you output\n"
        "   must come from the RAW SURFACE WEB CLAIMS or RAW ACADEMIC PAPERS blocks.\n"
        "   Use it for two things only: resolving what the user's new question refers\n"
        "   to, and avoiding re-reporting findings that were already covered.\n"
        "6. Do not withhold a genuinely relevant finding merely because it resembles an\n"
        "   earlier one. If the new question puts it in a different light, report it.\n\n"
        "REQUIRED STRUCTURE:\n"
        "<analysis>\n"
        "  <summary>Write a 2-3 sentence overview of the general trend here.</summary>\n"
        "\n"
        "  <consensus_point>\n"
        "    <point>Core technical concept where both align</point>\n"
        "    <web_quote>Exact snippet from web</web_quote>\n"
        "    <source_url>URL</source_url>\n"
        "    <paper_quote>Exact snippet from paper</paper_quote>\n"
        "    <source_paper_id>Paper ID</source_paper_id>\n"
        "  </consensus_point>\n"
        "\n"
        "  <contradiction_point>\n"
        "    <conflict_topic>Specific focus of disagreement</conflict_topic>\n"
        "    <web_claim>Web's stance</web_claim>\n"
        "    <web_quote>Exact snippet from web</web_quote>\n"
        "    <source_url>URL</source_url>\n"
        "    <paper_claim>Paper's opposing stance</paper_claim>\n"
        "    <paper_quote>Exact snippet from paper</paper_quote>\n"
        "    <source_paper_id>Paper ID</source_paper_id>\n"
        "  </contradiction_point>\n"
        "</analysis>"
    )

    # Findings only, capped to the last few turns — see agents/history.py.
    prior = format_prior_findings(state.get("conversation_history", []))
    prior_block = (
        f"--- EARLIER IN THIS THREAD (context only — NOT evidence, never quote it) ---\n"
        f"{prior}\n\n"
        if prior else ""
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=(
            f"Target Question: '{user_query}'\n\n"
            f"{prior_block}"
            f"--- RAW SURFACE WEB CLAIMS ---\n{web_data}\n\n"
            f"--- RAW ACADEMIC PAPERS ---\n{paper_data}\n\n"
            "Generate the tag-based analysis now."
        ))
    ]
    
    

    # ------------------------------------------------------------------
    # PASS 2: NATIVE REGEX PARSING (Bulletproof Extraction)
    # ------------------------------------------------------------------
    # The generation call and the cleanup share one guard: a dead API key or a
    # rate limit must degrade to an empty analysis, not escape the node.
    try:
        raw_xml_report = base_llm.invoke(messages).content

        # With no tools bound this is a plain string, but Anthropic can return
        # a list of content blocks — join them rather than crashing on .replace.
        if isinstance(raw_xml_report, list):
            raw_xml_report = "".join(
                block.get("text", "") for block in raw_xml_report if isinstance(block, dict)
            )

        # Clean any accidental markdown backticks the LLM might have generated
        clean_report = raw_xml_report.replace("```xml", "").replace("```html", "").replace("```", "").strip() # type: ignore
    except Exception as e:
        print(f"[CRITIC] LLM call failed: {type(e).__name__}: {e}")
        return {
            "overall_summary": "Critic analysis failed.",
            "consensus": [],
            "contradictions": []
        }
    
    
    # 1. Extract Summary
    overall_summary = extract_tag(clean_report, "summary")
    if overall_summary == "N/A":
        overall_summary = "Summary generation failed."
    
    # 2. Extract Consensus Points
    consensus_list = []
    c_blocks = re.findall(r"<consensus_point>(.*?)</consensus_point>", clean_report, re.DOTALL | re.IGNORECASE)
    for block in c_blocks:
        consensus_list.append({
            "point": extract_tag(block, "point"),
            "web_quote": extract_tag(block, "web_quote"),
            "paper_quote": extract_tag(block, "paper_quote"),
            "source_url": extract_tag(block, "source_url"),
            "source_paper_id": extract_tag(block, "source_paper_id")
        })
        
    # 3. Extract Contradiction Points
    contradiction_list = []
    x_blocks = re.findall(r"<contradiction_point>(.*?)</contradiction_point>", clean_report, re.DOTALL | re.IGNORECASE)
    for block in x_blocks:
        contradiction_list.append({
            "conflict_topic": extract_tag(block, "conflict_topic"),
            "web_claim": extract_tag(block, "web_claim"),
            "web_quote": extract_tag(block, "web_quote"),
            "source_url": extract_tag(block, "source_url"),
            "paper_claim": extract_tag(block, "paper_claim"),
            "paper_quote": extract_tag(block, "paper_quote"),
            "source_paper_id": extract_tag(block, "source_paper_id")
        })

    print(f"\n[DEBUG - REGEX PARSER] Extracted {len(consensus_list)} Consensus and {len(contradiction_list)} Contradictions.")
    
    return {
        "overall_summary": overall_summary,
        "consensus": consensus_list,
        "contradictions": contradiction_list
    }