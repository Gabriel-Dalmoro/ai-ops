from __future__ import annotations
import os
from typing import Optional

# --- simple token helpers (rough but safe for free tiers) ---
def estimate_tokens(text: str) -> int:
    # very rough: ~4 chars per token
    return max(1, len(text) // 4)

def truncate_by_tokens(text: str, max_tokens: int) -> str:
    if not text:
        return ""
    if estimate_tokens(text) <= max_tokens:
        return text
    char_budget = max_tokens * 4
    return text[:char_budget] + "\n…[truncated]"

# --- minimal LLM adapter ---
class LLM:
    """
    Minimal, pluggable LLM adapter with guardrails.

    Default backend is 'stub' (no cost). When ready, set:
      MODEL_BACKEND=gemini
      GEMINI_API_KEY=...   (in your .env)
    and implement the Gemini call where indicated.
    """

    def __init__(self, backend: Optional[str] = None):
        self.backend = (backend or os.getenv("MODEL_BACKEND", "stub")).lower()
        # Guardrail defaults – free-tier friendly; override via .env if needed
        self.max_prompt_tokens = int(os.getenv("MAX_PROMPT_TOKENS", "2000"))
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "500"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    def generate(self, prompt: str) -> str:
        # Enforce token budget on input
        safe_prompt = truncate_by_tokens(prompt, self.max_prompt_tokens)

        if self.backend == "stub":
            # Local stand-in so you can wire the pipeline with zero API cost
            return (
                "[STUB TAILOR OUTPUT]\n\n"
                + safe_prompt[:600]
                + "\n\n(This is stub output. Set MODEL_BACKEND=gemini and GEMINI_API_KEY to use a real model.)"
            )

        if self.backend == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError("Missing GEMINI_API_KEY in environment.")
            # TODO: implement Gemini call (google-generativeai SDK or REST)
            # Keep output capped to self.max_output_tokens.
            raise NotImplementedError("Gemini backend not wired yet; stay on stub for now.")

        raise ValueError(f"Unknown MODEL_BACKEND: {self.backend}")