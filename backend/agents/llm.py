# backend/agents/llm.py
"""Provider chain for the two LLM nodes: Anthropic primary, Gemini fallback.

Anthropic returned 529 Overloaded for several minutes during live testing,
which degraded every request in that window. Both reasoning nodes now call
through FallbackLLM, which tries providers in order and only fails if all of
them do. The .invoke(messages) surface is identical to a LangChain chat model,
so the nodes call it exactly as before.

The fallback is deliberately triggered by *any* exception, not just 5xx: a
schema validation failure or a timeout is just as fatal to the request, and
the second provider costs nothing when the first one is healthy.
"""
import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Import order used to decide this — web_scout happened to call load_dotenv()
# first. Doing it here makes the module safe to import on its own.
load_dotenv()

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
GEMINI_MODEL = "gemini-3.5-flash"


class FallbackLLM:
    """Drop-in chat model that walks a provider chain until one answers.

    Pass `schema` to get structured output; the schema is bound to every
    provider in the chain, so the fallback returns the same Pydantic type.
    """

    def __init__(self, temperature: float, schema=None):
        self.temperature = temperature
        self.schema = schema
        self._chain = None  # built lazily so importing never needs a key

    def _build_chain(self):
        chain = [(
            "anthropic",
            ChatAnthropic(model=ANTHROPIC_MODEL, temperature=self.temperature),  # type: ignore
        )]

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                chain.append((
                    "gemini",
                    ChatGoogleGenerativeAI(
                        model=GEMINI_MODEL,
                        temperature=self.temperature,
                        google_api_key=gemini_key,
                        # Without these the client retries silently for minutes
                        # on an unreachable model, which reads as a hang.
                        timeout=60,
                        max_retries=1,
                    ),
                ))
            except ImportError:
                print("[LLM] langchain-google-genai missing — no Gemini fallback.")
        else:
            print("[LLM] GEMINI_API_KEY not set — no Gemini fallback.")

        if self.schema is not None:
            chain = [(name, m.with_structured_output(self.schema)) for name, m in chain]

        return chain

    def invoke(self, messages):
        if self._chain is None:
            self._chain = self._build_chain()

        failures = []
        for index, (name, model) in enumerate(self._chain):
            try:
                result = model.invoke(messages)
                if index > 0:
                    print(f"[LLM] Served by fallback provider: {name}")
                return result
            except Exception as e:
                print(f"[LLM] {name} failed: {type(e).__name__}: {str(e)[:150]}")
                failures.append(f"{name}={type(e).__name__}")

        raise RuntimeError(f"All LLM providers failed ({', '.join(failures)})")

    async def astream_text(self, messages, on_chunk=None):
        """Stream a text completion, returning the full text at the end.

        `on_chunk` is awaited with the accumulated text so far, letting the
        caller push progress to the client. A provider that fails *after*
        emitting chunks falls through to the next one and the accumulated text
        is discarded — partial output is cosmetic, and the authoritative result
        is whatever the surviving provider returns.
        """
        if self._chain is None:
            self._chain = self._build_chain()

        failures = []
        for index, (name, model) in enumerate(self._chain):
            text = ""
            try:
                async for chunk in model.astream(messages):
                    piece = getattr(chunk, "content", "") or ""
                    if isinstance(piece, list):  # Anthropic content blocks
                        piece = "".join(
                            b.get("text", "") for b in piece if isinstance(b, dict)
                        )
                    if not piece:
                        continue
                    text += piece
                    if on_chunk is not None:
                        await on_chunk(text)
                if index > 0:
                    print(f"[LLM] Streamed by fallback provider: {name}")
                return text
            except Exception as e:
                print(f"[LLM] {name} stream failed after {len(text)} chars: "
                      f"{type(e).__name__}: {str(e)[:120]}")
                failures.append(f"{name}={type(e).__name__}")

        raise RuntimeError(f"All LLM providers failed ({', '.join(failures)})")
