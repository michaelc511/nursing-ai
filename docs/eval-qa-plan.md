# Eval & QA plan: prove quality at every layer

Goal: show, with numbers, that every quality layer of NurseOps Now earns its place, and that
the evals themselves can be trusted. Area 8 (Evaluation & QA) in `docs/features.md`, plus
the pieces of areas 3, 7 and 9 that evals measure.

Started 2026-11-19. Status: **TO DO** unless marked.

## Where we start (from `evaluation/baseline_live.json`)
| Metric | Score | Problem |
|---|---|---|
| hit@1 / hit@3 | 0.889 / 1.0 | Set too easy: nothing left to improve, so no layer can show a gain |
| review, retrieval, safety | 1.0 | Same: saturated |
| assist | 0.875 | OK |
| RAGAS faithfulness / answer relevancy | 0.893 / 0.725 | Single run, no spread |
| Golden set | 20 rows | Too small to trust a 0.05 gate |
| LLM judge | not checked against a human | Can't say the judge is right |
| CI live gate (F20) | skipped | No `ANTHROPIC_API_KEY` GitHub secret |

## Step 0: Realistic policy PDFs (DONE 2026-11-19)
The 3 policies were one page each (6-8 chunks), so every retrieval method scored 100%.
- Expanded to 5 pages each with 13 more sections (definitions, repeat and post-op imaging,
  prior imaging, contrast, special populations, review timelines, appeals, coding, history).
  The wording overlaps the coverage criteria on purpose (hard negatives).
- Pages 1-2 unchanged, so §2.A etc., page numbers and mock reviews still hold.
- Versions bumped (72148 v3.3, 73721 v2.2, 70551 v4.1) and re-embedded: 21 → 83 chunks.
- Source: `backend/scripts/make_samples.py --policies-only`.

| Offline (mock) | Before | After |
|---|---|---|
| hit@1 | 0.889 | 0.778 |
| hit@3 | 1.0 | 0.889 |
| Live: RAGAS faithfulness | 0.893 | 0.775 |
| Live: answer relevancy | 0.725 | 0.785 |
| Live: assist | 0.875 | 1.0 |
| retrieval | 1.0 | 0.889 |

The CI gate caught the drop (`GATE FAILED: hit@1 0.889 -> 0.778`); the mock baseline was then
re-saved because the corpus changed on purpose. The live baseline was re-run 2026-11-19 ($0.42) and re-saved. Faithfulness fell 0.893 → 0.775: more, similar chunks in the context, or run-to-run noise. Part E will tell which.

First findings for Part A:
- r5 "documents required for a knee MRI" now returns §17 Coding notes, not §3: a real miss.
- r8 "migraine with a normal neuro exam" wants §5, but new §9 (Migraine) is also right.
  Golden rows need a list of acceptable labels, not one.
- "my knee keeps giving out" ranks §6.B (definition) over §2.A (criterion): definition
  sections compete with criteria.

## Parts

### Part A: Bigger, harder golden set (Claude drafts, Mike reviews)
1. Grow `evaluation/golden.jsonl` from 20 to about 60 rows.
2. Add hard cases on purpose: paraphrases with no shared words, two criteria in one question,
   negations ("no red flags"), the wrong policy for the CPT, off-topic, and injection text.
3. Tag each row `difficulty: easy|hard` and `split: dev|test`. Tune on `dev` only; report on
   `test` only (a held-out set, so the numbers aren't overfit).
4. Mike reviews every label (`source: "Claude draft, Mike reviews"` stays).

Done when: hit@1 on `test` is below 0.9 with today's pipeline, so there is room to show gains.

### Part B: Full retrieval metrics (Claude)
1. `run_retrieval.py` reports hit@1, hit@3, **MRR** and **recall@k**, per difficulty and split.
2. Output JSON as well as text, so other scripts can read it.

### Part C: Ablation table, one layer at a time (Claude builds, Mike runs live)
New script `evaluation/run_ablation.py`, no LLM needed for retrieval rows:

| Run | Vector | BM25 hybrid | Query rewrite | Re-rank |
|---|---|---|---|---|
| 1 | on | off | off | off |
| 2 | on | on | off | off |
| 3 | on | on | on | off |
| 4 | on | on | on | on |

Plus a chunking row: fixed-size chunks vs clause-aware chunks (S14).
Writes `evaluation/ablation.json` and a markdown table. Uses the existing `settings.hybrid`
and re-ranker switches in `backend/app/rag/index.py`.

Done when: the table shows how much each layer adds on the `test` split.

### Part D: Trust the judge (Mike labels, Claude scores)
1. Pick 20 live answers. Mike marks each pass/fail for faithfulness and citations.
2. Compare to the LLM judge: % agreement and Cohen's kappa.
3. If agreement is under 80%, fix the judge prompt (versioned in `backend/prompts/`) and rerun.

Done when: "the judge agrees with a clinician-style review X% of the time" is a real number.

### Part E: Measure the noise (Mike runs, about $1-3 per run)
1. Run `run_evals.py --live` 3 times.
2. Report mean and spread per score.
3. Set the `--gate` threshold from that spread instead of a flat 0.05.

### Part F: Live CI gate catches a real regression (Mike + Claude)
1. Mike adds the `ANTHROPIC_API_KEY` GitHub secret (and a monthly spend cap).
2. Open a test PR with a deliberately worse prompt (e.g. drop the "cite page + quote" rule).
3. CI live gate fails it. Save the screenshot and log. Close the PR.

Done when: F20 is **Y** in `docs/features.md` and there is proof of a blocked PR.

### Part G: Production failure → golden case (Mike + Claude)
1. Take one weak answer seen live (N4 online monitoring or a thumbs down).
2. Add it to `golden.jsonl` with its fix; show the score before and after.

Done when: one documented loop: live failure → new test → fix → gate passes.

### Part H: Write-up (Claude)
`docs/eval-report.md` (+ `.html` via `tools/scripts/md_to_html.py`): golden set stats, ablation
table, judge agreement, noise, blocked PR, the feedback-loop example, and five interview lines.

## Order and size
A → B → C first (no API cost, biggest proof). Then D and E (small live cost), F (needs the
secret), G, and H last.

## Interview line (fill in the numbers at the end)
"I built a 60-question golden set with a held-out split, ablated each retrieval layer
(hybrid +X, re-rank +Y on MRR), checked my LLM judge against my own labels (Z% agreement),
set the CI gate from measured noise, and showed it blocking a bad prompt change."
