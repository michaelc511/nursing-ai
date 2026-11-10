# NurseOps Now features

Status of all 42 features from `claude-config/new-project/super-features.html` for this app (decided 2026-11-10, AI features checked on real Claude 2026-11-10).
**Y** = built; AI features also checked on real Claude unless noted · **To Do When LLM is ready** = still needs the GitHub secret or Phase 11 · **N/A - Optional** = optional, skipped. ← new = production / enterprise feature added 2026-11-10.

Totals: 35 Y · 3 To Do When LLM is ready · 4 N/A - Optional.

## Scope & Foundation
- F0 App Idea & Scope Design: Y
- F1 Prototype Execution: Y
- F4/S16 FastAPI Backend: Y
- F12 Engine Strategy Factory: Y
- F12.1 Parallel Entry Point: Y ← new (AI-MK engine frozen as a baseline next to LangGraph)

## Ingestion & Indexing
- F3 Semantic RAG & Vector Store: Y
- S14 Clause-Aware Chunking: Y
- S4 Metadata Extraction: Y
- N1 Document Parsing (OCR/tables): Y ← new
- N2 Incremental Re-index + Versioning: Y

## Retrieval Quality
- F18/S9 Hybrid Search: Y
- F10/S10 Cross-Encoder Re-ranking: Y
- S8 Query Rewriting: Y

## Prompting & Generation
- F3.1 System Prompt & Persona: Y
- F2 Dynamic LLM Selector: Y ← new
- N3 Semantic Cache + Model Fallback: Y ← new (cache checked live; fallback tested with mocks. Claude down -> needs review, never a silent mock in prod)

## Agents & Tools
- F13/S17 LangGraph Engines: Y
- F13.1 LangGraph State Machine: Y
- F13.2 Agentic RAG: Y
- F11 Text-to-SQL: N/A - Optional (optional; agent tools call services/)
- F8 FastMCP Server: Y
- F14 CrewAI: N/A - Optional (optional)
- F15 AutoGen: N/A - Optional (optional)

## Memory
- F7 Chat Memory: Y
- F16 Persistent Checkpointing: Y

## Safety, Security & Privacy
- F22 Prompt-Injection Defense: Y
- F19 Intent Gating: Y
- S5 PII Sanitization: Y ← new (logs, traces, chat history)
- F21/S21 Auth, Rate Limiting & RBAC: Y
- N5 Red Teaming: Y ← new (44 attacks on real Claude, 0 failed)

## Evaluation & QA
- F17 RAG Evals Harness: Y (live baseline saved)
- F20 CI Eval Gate: To Do When LLM is ready (offline gate works; live gate needs the GitHub secret)
- F23 Unit Tests: Y

## Observability & Cost
- F9 Tracing: Y
- F6 Token & Cost Accounting: Y
- N4 Online Quality Monitoring: Y ← new

## Interfaces & Deployment
- F5 Web Interfaces: Y
- F24 Deploy: To Do When LLM is ready (Phase 11)
- N8 Production Ops & Compliance: To Do When LLM is ready ← new (Phase 11)

## Governance & Process
- N6 AI Governance: Y ← new (Phase 11)
- F25 Retro & Memory: Y

## Emerging
- N7 GraphRAG / Multimodal: N/A - Optional (optional)
