import re
from agents.history import format_prior_findings
from agents.llm import FallbackLLM
from graph.state import TarkaState
from langchain_core.messages import SystemMessage, HumanMessage

# --- LLM INITIALIZATION ---
# Anthropic primary, Gemini fallback — see agents/llm.py.
base_llm = FallbackLLM(temperature=0.4)

# --- PROMPTS ---
# Both modes emit the identical tag schema, so the regex parser below and the
# UI contract are unaffected by which one runs.
_XML_STRUCTURE = (
    "REQUIRED STRUCTURE:\n"
    "<analysis>\n"
    "  <summary>See the summary rule above.</summary>\n"
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

_SHARED_RULES = (
    "1. Do NOT use Markdown formatting. Do NOT include conversational filler.\n"
    "2. Only output the requested tags and their contents.\n"
    "3. If you find no consensus or no contradictions, simply omit those specific tags.\n"
    "4. Output 'N/A' for any missing URLs or Paper IDs — but NEVER for a quote.\n"
    "5. Every consensus_point and contradiction_point REQUIRES a real, verbatim\n"
    "   quotation from BOTH the web sources AND the academic papers. If one side\n"
    "   is silent on a matter, there is no finding — omit it entirely. Absence of\n"
    "   evidence is NOT disagreement. Never write 'N/A', 'not addressed', 'the\n"
    "   papers do not discuss this' or anything similar into a quote or claim\n"
    "   field; a point you cannot quote both sides of does not get reported.\n"
    "6. An EARLIER IN THIS THREAD section may appear below. It is NOT evidence.\n"
    "   It records conclusions you already drew, not sources. Never quote it, cite\n"
    "   it, or treat any finding in it as established fact. EVERY quote you output\n"
    "   must come from the RAW SURFACE WEB CLAIMS or RAW ACADEMIC PAPERS blocks.\n"
)

# Turn 1: nothing has been examined yet. Survey the corpus.
_DISCOVERY_RULES = (
    "You are an adversarial expert research evaluator cross-examining public claims against peer-reviewed evidence.\n"
    "Your objective is to thoroughly analyze the raw text blocks and output your findings using STRICT XML tags.\n\n"
    "RULES:\n"
    + _SHARED_RULES +
    "7. <summary> is a 2-3 sentence overview of the general trend across both sides.\n"
    "8. Report every substantive point of agreement and disagreement you can support\n"
    "   with quotes from both sides.\n\n"
)

# Turn 2+: the corpus is already mined and the findings are listed above.
# The task is to answer one question, not to survey again.
_INTERROGATION_RULES = (
    "You are an adversarial expert research evaluator answering a FOLLOW-UP question\n"
    "about a corpus you have ALREADY analysed. This is not a fresh survey. The sources\n"
    "below have been examined and the findings so far are listed in EARLIER IN THIS\n"
    "THREAD. The user is now asking one specific thing about them.\n\n"
    "RULES:\n"
    + _SHARED_RULES +
    "7. <summary> must DIRECTLY ANSWER the user's question, using the corpus as evidence.\n"
    "   Do not write a general overview of the topic — that has already been given.\n"
    "   Answer in the first sentence. Never restate the question, never narrate what is\n"
    "   being asked, and never refer to 'the user'. Write the answer, not a preamble.\n"
    "8. Emit <consensus_point> or <contradiction_point> ONLY for findings that BOTH\n"
    "   (a) bear directly on this specific question, AND (b) were NOT already reported\n"
    "   in EARLIER IN THIS THREAD.\n"
    "9. Restating an earlier finding in different words is a FAILURE. If the corpus\n"
    "   offers nothing new for this question, emit no such tags at all — a well-argued\n"
    "   <summary> on its own is a complete and correct answer here.\n"
    "10. An earlier finding may be re-reported ONLY if this question puts genuinely new\n"
    "    evidence behind it. In that case the <point> must state what is new.\n\n"
)


# --- HELPER PARSER FUNCTION ---
def extract_tag(text: str, tag: str) -> str:
    """Safely extracts text between XML tags using Regex."""
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"


# Phrases the model reaches for when one side has nothing to say. A finding
# built on one of these is describing silence, not disagreement.
_NON_QUOTES = ("n/a", "none", "not addressed", "not available", "no quote",
               "not applicable", "no direct", "does not address", "-", "—")


def _is_grounded(finding: dict) -> bool:
    """A finding is only real if BOTH sides are backed by an actual quotation.

    Source URLs and paper IDs may legitimately be missing; the quotes may not.
    """
    for key in ("web_quote", "paper_quote"):
        quote = (finding.get(key) or "").strip()
        if len(quote) < 12 or quote.lower().strip(".") in _NON_QUOTES:
            return False
        if any(quote.lower().startswith(p) for p in _NON_QUOTES if len(p) > 3):
            return False
    return True

_SUMMARY_OPEN = re.compile(r"<summary>", re.IGNORECASE)


def _partial_summary(text: str) -> str:
    """The summary is the first tag the model writes, so it can be shown while
    the rest of the analysis is still generating."""
    opened = _SUMMARY_OPEN.search(text)
    if not opened:
        return ""
    body = text[opened.end():]
    closed = re.search(r"</summary>", body, re.IGNORECASE)
    return (body[: closed.start()] if closed else body).strip()


async def critic_two_pass_node(state: TarkaState) -> dict:
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
    # A follow-up runs against a corpus that has already been mined. Asking it
    # the discovery question again ("what do these sources disagree about?")
    # makes re-deriving the same findings the correct answer — which is why
    # instructing it not to repeat itself never worked. Different job, different
    # prompt; the output schema is identical so parsing and the UI don't change.
    is_followup = not state.get("needs_fetch", True)
    system_instruction = (
        _INTERROGATION_RULES if is_followup else _DISCOVERY_RULES
    ) + _XML_STRUCTURE
    print(f"[CRITIC] Mode: {'interrogation (follow-up)' if is_followup else 'discovery (fresh)'}")

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
    # The server puts a queue here when it wants live progress; absent in the
    # headless harness and in tests, where streaming simply doesn't happen.
    queue = state.get("_partial_queue")
    last_sent = ""

    async def push_partial(accumulated: str) -> None:
        nonlocal last_sent
        if queue is None:
            return
        summary = _partial_summary(accumulated)
        # Only worth a frame if it grew meaningfully — token-level updates
        # would flood the SSE channel for no visible benefit.
        if summary and len(summary) - len(last_sent) >= 24:
            last_sent = summary
            await queue.put(("partial", summary))

    try:
        raw_xml_report = await base_llm.astream_text(messages, on_chunk=push_partial)

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

    # 4. Drop findings that aren't grounded on both sides.
    #
    # The model will occasionally emit a contradiction whose paper side reads
    # "Academic papers do not directly address this claim" with a quote of
    # "N/A" — absence of evidence written up as opposition. That is the exact
    # failure this project exists to prevent, and prompt rules alone don't
    # stop it, so it's enforced here where the outcome is deterministic.
    kept_consensus = [c for c in consensus_list if _is_grounded(c)]
    kept_contradictions = [c for c in contradiction_list if _is_grounded(c)]

    dropped = (len(consensus_list) - len(kept_consensus)) + \
              (len(contradiction_list) - len(kept_contradictions))
    if dropped:
        print(f"[CRITIC] Dropped {dropped} ungrounded finding(s) — a quote was "
              f"missing from one side.")

    print(f"\n[DEBUG - REGEX PARSER] Extracted {len(kept_consensus)} Consensus and {len(kept_contradictions)} Contradictions.")

    return {
        "overall_summary": overall_summary,
        "consensus": kept_consensus,
        "contradictions": kept_contradictions
    }