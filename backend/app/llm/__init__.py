"""LLM layer (Phase 4): one place that talks to Claude.

- F2   model selector: CLAUDE_MODEL default, CLAUDE_MODELS allowed list, switchable in demo mode.
- F6   every call recorded in llm_calls (tokens, cost, latency); prompts are never stored.
- N3   exact-input cache + fallback model; if every model fails -> LLMUnavailable (the caller
       sends the case to a person; production never falls back to mock answers silently).
"""
