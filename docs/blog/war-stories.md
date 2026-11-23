# War stories: problems we hit and the fix that worked

:::html
<style>.tags{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:4px 0 10px;font-size:.88em}
.tags b{color:var(--muted);font-weight:600}.tags a{text-decoration:none;border:1px solid var(--accent);border-radius:14px;padding:2px 10px;
background:color-mix(in srgb,var(--accent) 10%,transparent);color:var(--fg)}.tags a:hover{background:color-mix(in srgb,var(--accent) 22%,transparent)}
.tags small{color:var(--muted)}.tags .flow{flex-basis:100%;color:var(--muted);font-size:.95em}</style>
<div class="tags"><b>Tags:</b>
<a href="#war-story-1-s14-half-the-configuration-steps-fixed-by-chunking-on-headings">1 · Chunking <small>S14 · S4 · F18/S9 · F10/S10 · N1 · N2</small></a>
<a href="#war-story-2-f17-f20-the-eval-said-100-fixed-by-making-the-test-as-hard-as-real-life">2 · Evals <small>F17 · F20</small></a>
<div class="flow">the problem → what we tried → what worked → the lesson</div></div>
:::

Nov 22, 2026 · Michael Chang · Live demo: nurseops-now.fly.dev · Status: 2 stories

**Read in this order**

1. [Why this post](#why-this-post) and [Words used in this post](#words-used-in-this-post): the goal and the terms
2. [War story 1 (S14): half the configuration steps, fixed by chunking on headings](#war-story-1-s14-half-the-configuration-steps-fixed-by-chunking-on-headings): enterprise product docs, chunking by headings
3. [War story 2 (F17, F20): the eval said 100%, fixed by making the test as hard as real life](#war-story-2-f17-f20-the-eval-said-100-fixed-by-making-the-test-as-hard-as-real-life): enterprise product docs, an honest eval
4. [What this proves](#what-this-proves)

## Why this post

Interviewers ask "tell me about a time you hit a hard problem." Each story here is a problem from enterprise business software and domain-knowledge documents, the methods tried, and the fix that worked. Every fix is one NurseOps Now actually builds, so each story names its feature numbers (F, S and N in super-features) and links back to the pages that explain them.

Pages that link here open this page in a new tab. Close the tab, or use the **Back** links at the end of each story, to return.

**In plain terms:** a folder of short "here's what broke and how we fixed it" stories, each pinned to the feature that does the fixing.

## Words used in this post

| Term | Plain meaning | Everyday example |
|---|---|---|
| War story | A real problem, what was tried, and what fixed it | "The time the printer jammed before the board meeting" |
| Chunk | One small piece of a long document, stored for search | One index card cut from a binder |
| Contextual header | A label on each chunk saying where it came from | The binder name and page written on top of each card |
| Pre-filter | Narrowing the search before ranking results | Only looking in the Procurement drawer |
| Re-ranking | A second, careful sort of the search results | A librarian double-checking the pile before handing it over |
| Eval | A repeatable test that scores the assistant's answers | A practice exam with an answer key |
| CI gate | An automatic test run on every change; a lower score blocks it | A building inspector who must sign off |
| Baseline | The saved score a new change is compared against | Last semester's grade |

## War story 1 (S14): half the configuration steps, fixed by chunking on headings

**Features:** **S14 Clause-Aware Chunking** (the main fix) · S4 Metadata Extraction · F18/S9 Hybrid Search · F10/S10 Cross-Encoder Re-ranking · N1 Document Parsing · N2 Incremental Re-index & Doc Versioning

**Issue → solution:** answers came back with half a procedure or the wrong product version → chunk by the document's own headings, and label every chunk.

**War story: "The assistant kept giving half the configuration steps"**

**The situation.** At work we built an internal assistant for support engineers and implementation consultants. It answered questions from our enterprise software documentation: admin guides, configuration manuals, release notes, integration specs and internal domain knowledge like billing rules, approval workflows and tax handling by region. The documents were long and heavily structured, with nested headings, numbered steps, prerequisites, notes and "applies to version X" callouts.

**The problem.** Answers were often _almost_ right. Someone would ask "how do I set up multi-level approval for purchase orders?" and get steps 1–4 but not steps 5–7. Or the answer missed the warning that this only works when a certain module is enabled. Sometimes it mixed instructions from two product versions, or pulled a similar-looking procedure from a different module. For a consultant configuring a customer's system, half the steps or the wrong version is worse than no answer.

**What we tried:**

1. **Fixed-size chunks (N tokens).** These were the easiest to build and the worst results. The cutoffs landed in the middle of procedures, so the prerequisites ended up in one chunk and the steps in another. Retrieval found one piece and the model answered as if it had the whole thing.
2. **Fixed-size with overlap.** This helped a little, but it bloated the index, still cut long procedures, and filled the top results with near-duplicates.
3. **Paragraph or sentence splitting.** The pieces were cleaner, but they had no context. A chunk saying "Set the threshold to the approval limit" didn't say _which_ module, feature or version it belonged to, so purchase-order and expense-approval chunks looked the same to the embeddings.
4. **Embedding-based semantic chunking.** It was smarter in theory, but the boundaries shifted every time we re-indexed. It also didn't match how the docs were organized, so citations were hard to trace back.
5. **Stuffing whole documents into the prompt.** That worked for a short release note but was far too slow and expensive for a 300-page admin guide.

**What actually worked: chunk by the document's own headings, and label every chunk.**

- **We split on structure, not size.** One chunk per heading section or per complete procedure, following the doc's own hierarchy (H1 > H2 > H3). A procedure is never cut in half, and its prerequisites and warnings stay with the steps.
- **We added a contextual header to every chunk.** Each one starts with a breadcrumb such as `[Admin Guide v<version> | Procurement module | Approvals > Multi-level approval | page/URL]`. The embedding now carries where the chunk lives, and every citation points to an exact section.
- **We set a size cap as a fallback.** Only sections over a set length are split further, and the split happens at sub-headings or step boundaries, never mid-step. Boilerplate like nav menus, page headers, footers and legal text is stripped first.
- **We put metadata on every chunk**: product, module, version, doc type, section and audience (admin or end user). Search **pre-filters** on these before ranking, so a question about version 2024.2 of Procurement never gets an answer from 2022 or from the Expenses module.
- **We added hybrid search plus re-ranking.** Keyword search (BM25) catches exact terms like field names, error codes and setting names that embeddings tend to blur. Embeddings catch the meaning, and a cross-encoder re-ranks the results so the most relevant section comes first.
- **We re-index per document.** When a new release ships, only that guide's chunks are replaced, and the version lives in both the header and the metadata.

**The result.** Fewer, complete chunks. Answers came back with every step plus the prerequisites and warnings, citations linked to the exact section, and the version mix-ups stopped. Support engineers began trusting the answers enough to paste the cited section straight into customer tickets.

**Trade-offs I'd mention:** heading-based chunking needs a parser per format (HTML help sites, PDFs, Word, Confluence exports), and it depends on authors actually using headings properly. For unstructured content like old wiki pages or exported emails, I'd fall back to fixed-size chunks with overlap and measure the retrieval hit rate on a test question set rather than assume.

**The lesson:** chunk the way people use the document. Consultants follow one procedure or one feature section at a time, so each chunk should be one complete section, labeled with product, module and version.

**Short version for an interview (about 30 seconds):**
"Our support assistant over enterprise product docs kept returning half a configuration procedure or mixing product versions. We tried fixed-size chunks, overlap, paragraph splitting and semantic chunking, and they all cut procedures or lost context. What fixed it was chunking by the doc's own headings, one complete section per chunk, with a breadcrumb header on each chunk and metadata for product, module and version that we pre-filter on. Add hybrid search and a re-ranker, and answers came back complete and cited to the exact section."

**Where this fix lives in NurseOps Now**

| Part of the fix | Feature | Where it's explained |
|---|---|---|
| Split on structure, not size; contextual header; size cap | S14 Clause-Aware Chunking | [Feature blog](nurseops-now-blog.html#p-s14) · [Detailed blog](nurseops-now-blog.html?defs=y#p-s14) · [Eval plan, Step 1](nurseops-now-evals.html#step-1-ingestion) · [Ingestion deep dive](deep-dives/01-ingestion.html#why-we-ingest-this-way) |
| Metadata on every chunk, pre-filter | S4 Metadata Extraction | [Detailed blog](nurseops-now-blog.html?defs=y#p-s4) |
| Keyword + meaning search | F18/S9 Hybrid Search | [Eval plan, Step 5](nurseops-now-evals.html#step-5-hybrid-search) |
| Cross-encoder re-rank | F10/S10 Cross-Encoder Re-ranking | [Eval plan, Step 6](nurseops-now-evals.html#step-6-re-ranking) |
| Parser per format, strip boilerplate | N1 Document Parsing | [Detailed blog](nurseops-now-blog.html?defs=y#p-n1) |
| Re-index per document, version in header | N2 Incremental Re-index & Doc Versioning | [Detailed blog](nurseops-now-blog.html?defs=y#p-n2) |

The work setting in this story is generic; the NurseOps Now numbers (21 chunks for three policies, the 1,200-character fallback) are in the linked pages.

**In plain terms:** cut the manual where its own chapters end, write the chapter name on every piece, and only search the right manual.

**Back to where you came from:** [Feature blog, S14](nurseops-now-blog.html#p-s14) · [Detailed blog, S14](nurseops-now-blog.html?defs=y#p-s14) · [Eval plan, Step 1: Ingestion](nurseops-now-evals.html#step-1-ingestion) · [Ingestion deep dive](deep-dives/01-ingestion.html#interview-answer) (or close this tab)

[↑ Back to the list](#why-this-post)

## War story 2 (F17, F20): the eval said 100%, fixed by making the test as hard as real life

**Features:** **F17 RAG Evals Harness** and **F20 CI/CD Eval Regression Gate** (the main fix)

**Issue → solution:** every retrieval method scored 100%, so the test proved nothing → make the test documents as long and overlapping as the real ones, and let the CI gate judge.

**War story: "Our eval said 100%, and that was the problem"**

**The situation.** At work we built an internal assistant that answered support and implementation questions from our enterprise product documentation: admin guides, configuration manuals and release notes. Before rolling it out, we built an eval: a set of real questions with known right answers, a retrieval score for each, and a CI gate that blocked any change that lowered the score.

**The problem.** Every retrieval method we tried scored 100%. Keyword search, embeddings and hybrid search all found the right section every time. That looked great, but it meant the test was useless. The test documents were short, clean sample pages, and the assistant first narrows the search to one product guide, so it only had to choose among a handful of sections. A test everyone passes proves nothing.

**What we did.** We made the test documents realistic. We replaced the sample pages with full-length guides, the way customers actually see them: glossaries, prerequisites, troubleshooting, version notes, and release notes that repeat the admin guide's wording. Much of the new text deliberately overlapped the procedures we were testing, the way real documentation does. We kept the original sections unchanged so existing answers and citations still held, bumped the document versions and rebuilt the index.

**The result.** The scores dropped, and the CI gate caught the drop on its own and failed the build. That was the gate doing its job. Because we had changed the documents on purpose, we reviewed the drop, then saved a new baseline.

**What it exposed.** Real problems the easy test had hidden:

- A question about which permissions a setup needs returned a release-notes mention instead of the prerequisites section.
- Some questions had two correct sections, so the answer key had to allow more than one right answer.
- Glossary definitions started outranking the actual procedure, the way they compete in real docs.

**What's next.** Before changing the retrieval, we ran the live eval several times to separate real drops from run-to-run noise.

**The lesson:** make the test as hard as real life, even when the numbers get worse. Lower numbers from an honest test beat 100% from an easy one.

**Short version for an interview (about 30 seconds):**
"Our first eval scored 100% on every retrieval method, which told me the test was too easy. We swapped the short sample pages for full-length, overlapping product docs, the scores dropped, and our CI gate caught it on its own. The harder test exposed real misses: release notes beating the prerequisites section, questions with two right answers, and definitions outranking procedures. Lower numbers from an honest test beat 100% from an easy one."

**Where this fix lives in NurseOps Now (the real numbers)**

The work setting in this story is generic. These are the measured results from NurseOps Now, on the same problem:

| What happened | NurseOps Now result | Where it's explained |
|---|---|---|
| The easy test | 1-page policies, 6–8 sections each; every method scored 100% | [Eval plan, Step 0](nurseops-now-evals.html#step-0-done-the-test-was-too-easy) |
| Made the test realistic | Policies expanded to 5 pages; 21 → 83 chunks; versions bumped (lumbar 3.3, knee 2.2, brain 4.1) | [Eval plan, Step 0](nurseops-now-evals.html#step-0-done-the-test-was-too-easy) |
| Scores (offline) | hit@1 0.889 → 0.778; hit@3 1.0 → 0.889 | [Eval plan, Step 10: Offline evals](nurseops-now-evals.html#step-10-offline-evals) |
| Score (live, real Claude, $0.42) | Faithfulness 0.893 → 0.775 | [Eval plan, Step 0](nurseops-now-evals.html#step-0-done-the-test-was-too-easy) |
| The gate | `GATE FAILED: hit@1 0.889 -> 0.778` (F20) | [Eval plan, Step 11: CI gate](nurseops-now-evals.html#step-11-ci-gate) · [Feature blog, F20](nurseops-now-blog.html#p-f20) |
| The harness | Golden set, retrieval and live scores (F17) | [Feature blog, F17](nurseops-now-blog.html#p-f17) |
| Real misses found | Knee MRI "required documents" returned *Coding notes*; migraine had two right sections; a definition outranked the coverage rule | [Eval plan, Step 0](nurseops-now-evals.html#step-0-done-the-test-was-too-easy) |

**In plain terms:** testing a librarian on one shelf proves nothing. Put them in the full library, with books that have nearly the same title, and you learn whether they're actually good.

**Back to where you came from:** [Eval plan, Step 0](nurseops-now-evals.html#step-0-done-the-test-was-too-easy) (or close this tab)

[↑ Back to the list](#why-this-post)

## What this proves

The choices in NurseOps Now aren't one-offs for medical policies. Cutting at the document's own structure (story 1) and testing on documents as hard as the real ones (story 2) solve the same problems in enterprise product documentation, and each story's NurseOps Now table shows the measured proof.

All NurseOps Now policies and cases are synthetic. No real patient data is used.
