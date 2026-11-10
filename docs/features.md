# NurseOps Now features

Status of all 42 features from `claude-config/super-features.html` for this app (decided 2026-11-10).
**Y** = built, or built on "go" without an AI key · **To Do When LLM is ready** = needs the AI key (or Phase 11) · **N/A - Optional** = optional, skipped. ← new = production / enterprise feature added 2026-11-10.

Totals: 23 Y · 15 To Do When LLM is ready · 4 N/A - Optional.

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
- S8 Query Rewriting: To Do When LLM is ready

## Prompting & Generation
- F3.1 System Prompt & Persona: To Do When LLM is ready
- F2 Dynamic LLM Selector: To Do When LLM is ready ← new
- N3 Semantic Cache + Model Fallback: To Do When LLM is ready ← new (Claude down -> needs review, never a silent mock in prod)

## Agents & Tools
- F13/S17 LangGraph Engines: To Do When LLM is ready
- F13.1 LangGraph State Machine: To Do When LLM is ready
- F13.2 Agentic RAG: To Do When LLM is ready
- F11 Text-to-SQL: N/A - Optional (optional; agent tools call services/)
- F8 FastMCP Server: Y
- F14 CrewAI: N/A - Optional (optional)
- F15 AutoGen: N/A - Optional (optional)

## Memory
- F7 Chat Memory: To Do When LLM is ready
- F16 Persistent Checkpointing: To Do When LLM is ready

## Safety, Security & Privacy
- F22 Prompt-Injection Defense: Y
- F19 Intent Gating: Y
- S5 PII Sanitization: Y ← new (logs, traces, chat history)
- F21/S21 Auth, Rate Limiting & RBAC: Y
- N5 Red Teaming: To Do When LLM is ready ← new

## Evaluation & QA
- F17 RAG Evals Harness: To Do When LLM is ready
- F20 CI Eval Gate: To Do When LLM is ready
- F23 Unit Tests: Y

## Observability & Cost
- F9 Tracing: Y
- F6 Token & Cost Accounting: Y
- N4 Online Quality Monitoring: To Do When LLM is ready ← new

## Interfaces & Deployment
- F5 Web Interfaces: Y
- F24 Deploy: To Do When LLM is ready (Phase 11)
- N8 Production Ops & Compliance: To Do When LLM is ready ← new (Phase 11)

## Governance & Process
- N6 AI Governance: Y ← new (Phase 11)
- F25 Retro & Memory: Y

## Emerging
- N7 GraphRAG / Multimodal: N/A - Optional (optional)
