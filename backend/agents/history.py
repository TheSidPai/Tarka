# backend/agents/history.py
"""Reading the conversation history that the client accumulates.

The server is stateless, so the client sends the thread back on every request.
Each entry is one completed turn:

    {
      "question": str,
      "summary": str,
      "consensus_points": [str, ...],
      "contradiction_topics": [str, ...],
    }

Only findings are carried, never quotes or source text. Prior findings are
inferences over a corpus, not evidence — the Critic must keep re-deriving
every quote from the raw sources, or errors compound across turns.
"""
from typing import List

# Findings accumulate every turn. The corpus already runs ~37k characters in
# the Critic prompt, so history is capped rather than grown without bound.
MAX_TURNS = 3


def recent(history: List[dict]) -> List[dict]:
    entries = [e for e in (history or []) if isinstance(e, dict)]
    return entries[-MAX_TURNS:]


def prior_questions(history: List[dict]) -> List[str]:
    """Every question asked so far, oldest first — used to stop the
    Synthesizer suggesting a follow-up the user has already clicked."""
    return [q for e in (history or []) if isinstance(e, dict) and (q := e.get("question"))]


def format_prior_findings(history: List[dict]) -> str:
    """A compact block of what earlier turns established.

    Returns "" when there is nothing to report, so callers can omit the
    section entirely rather than showing the model an empty heading.
    """
    entries = recent(history)
    if not entries:
        return ""

    blocks = []
    for i, entry in enumerate(entries, start=1):
        lines = [f"Turn {i} question: {entry.get('question', 'N/A')}"]

        topics = [t for t in entry.get("contradiction_topics", []) if t]
        if topics:
            lines.append("  Contradictions already reported: " + "; ".join(topics))

        points = [p for p in entry.get("consensus_points", []) if p]
        if points:
            lines.append("  Consensus already reported: " + "; ".join(points))

        blocks.append("\n".join(lines))

    return "\n".join(blocks)
