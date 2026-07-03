"""Engine 5 — AI Reasoning. The ONLY module allowed an LLM client. Exposes
exactly two operations: extract_intent() (Stage 1) and narrate() (Stage 10,
number-echo validated + template fallback). Never calculates reward values.
Built in build-plan Phase 5."""
