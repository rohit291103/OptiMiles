"""Engine 5 — AI Reasoning. The ONLY module allowed an LLM client. Exposes
exactly two operations: extract_intent() (Stage 1) and narrate() (Stage 10,
number-echo validated + template fallback). Never calculates reward values.
Built in build-plan Phase 5."""

from app.ai_reasoning.intent import ScopeRefusal, extract_intent
from app.ai_reasoning.model import ChatModel, model_from_settings
from app.ai_reasoning.narration import NarrationPayload, build_narration_payload, narrate

__all__ = [
    "ChatModel",
    "NarrationPayload",
    "ScopeRefusal",
    "build_narration_payload",
    "extract_intent",
    "model_from_settings",
    "narrate",
]
