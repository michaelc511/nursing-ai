# NurseOps Now AI governance

Scope: the NurseOps Now prototype, using synthetic data only. Items marked **Production** are needed before any real patient data. Owner of every item: Mike Chang.

## Core rules
- AI never approves or denies. A Nurse can approve or pend. Only a Medical Director can deny. The service layer enforces this.
- Every AI claim cites a source. Code checks each quote against the document, and a quote that can't be found sends the case to needs review.
- Every decision is audited: AI output, human decision, override flag, person and time.
- MCP has no decision tool, so Claude Cowork can't approve, pend or deny.

## Prompt and model versioning
- Prompts are versioned files in `backend/app/prompts/`. A meaning change gets a new file, for example `review_v1.md` to `review_v2.md`.
- Each AI review stores the prompt version that produced it (`ai_reviews.prompt_version`).
- The model comes from `CLAUDE_MODEL` (default `claude-opus-5-5`) with an allowed list in `CLAUDE_MODELS`. The fallback model is `CLAUDE_FALLBACK_MODEL`.
- Every AI call records its model, tokens, cost and latency in `llm_calls`. Prompts are not stored there.

## Eval-gated change approval
Any change to a prompt, model, retrieval setting or guardrail follows these steps:
1. Run `python ../evaluation/run_evals.py --gate` offline.
2. Run `python ../evaluation/run_evals.py --live --gate` and `python ../evaluation/redteam.py --live` on real Claude.
3. The gate fails if a score drops more than 0.05 against the baseline, or if any safety case fails.
4. Only update `evaluation/baseline_live.json` after a person reviews the new results.

CI runs the offline gate on every push. The live gate runs only once the `ANTHROPIC_API_KEY` GitHub secret is set.

## Model card
| Item | Detail |
| --- | --- |
| System | NurseOps Now case review and AI Assist |
| Model | Claude (`claude-opus-5-5` by default) |
| Intended use | Prepare prior authorization cases for a nurse: extract details, check completeness, compare with policy, draft provider requests |
| Not for | Making or communicating coverage decisions, or use without a human reviewer |
| Inputs | Request documents as PDFs, retrieved policy clauses, user questions |
| Outputs | Structured review JSON with citations and a suggested tier; cited AI Assist answers |
| Scope covered | Three imaging policies: CPT 72148, 73721, 70551 |

**Latest live evaluation (2026-11-10)**

| Measure | Score |
| --- | --- |
| Retrieval hit@3 | 1.0 |
| Retrieval hit@1 | 0.889 |
| Reviews | 1.0 (3 cases) |
| AI Assist, including LLM judge | 0.875 (8 checks) |
| Safety cases | 1.0 |
| Red team on real Claude | 44 attacks, 0 failed |
| RAGAS faithfulness | 0.893 |
| RAGAS answer relevancy | 0.725 |
| RAGAS context precision | 1.0 |

**Known limitations**
- The evaluation set is small: 20 cases on synthetic documents. It doesn't show performance on real faxes.
- AI Assist can mention details its tools did not return. An LLM judge scored one case question 3 out of 5 for faithfulness.
- Model fallback has been tested with mocks only.
- Only three imaging policies are covered.

## Risk register
| Risk | Impact | Control in place | Remaining action |
| --- | --- | --- | --- |
| AI makes or implies a coverage decision | High | Service-layer rule, no decision tool, red-team checks | Keep the safety gate at 100% |
| Invented or wrong citation | High | Code checks each quote; unverified quotes go to needs review | Add AI Assist citation checks |
| Prompt injection in a document | High | Documents treated as data, guardrails, forced needs review | Extend red team with real fax patterns |
| Real patient data enters the prototype | High | Synthetic-data rule, PII redaction in logs, traces and chat | **Production:** BAA, encryption review, access controls |
| Nurses over-trust AI suggestions | High | Tier is only a suggestion, override rate tracked | **Production:** review override and error samples regularly |
| Claude outage | Medium | Fallback model, then the case goes to a person with a warning | Test fallback on real Claude |
| Runaway AI cost | Medium | Per-user rate limit, cost cap per case, daily cap | Set a spend limit in the Anthropic console |
| Model or prompt change lowers quality | Medium | Versioning and eval gate | Add the GitHub secret for the live gate |
| Unauthorized access | Medium | Login, role rules, no public password hint, 24-hour lockout per network address after 3 wrong passwords | **Production:** SSO and individual accounts |
| Presenter switches used by a signed-in user | Low | Demo mode only, password required, AI mode changes audited | **Production:** `DEMO_MODE` off |

## Data-use policy
- This prototype uses synthetic documents only. Do not upload real patient information.
- Request documents go to the Claude API for review. Policy and guide search runs locally, and patient documents are never added to the search index.
- OCR and embeddings run locally.
- Prompts are not stored in `llm_calls`. Traces record timings, tokens and cost without content.

**Production:** a signed BAA with every vendor that touches PHI, encryption at rest and in transit, and role-based access are required first. Retention follows [production-ops.md](production-ops.md).
