"""Hover definitions for blog pages built by md_to_html.py (same idea as nurseops-now-blog.html?defs=y).

Every use of a glossary term in a paragraph, list item or table cell is highlighted, shows a hover box
with its plain-English meaning, and links to its entry in a generated "Key terms" glossary at the end;
the entry's "Back" link returns to the exact spot clicked. A "(definition)" after each term is shown
only when the URL has ?defs=1 (or the page's "Show definitions" link is clicked). Format guide:
claude-config/blog-format/BLOGFORMAT.md.
"""
from __future__ import annotations

import html
import re

# term -> plain meaning. Longer terms are matched first, so "hybrid search" wins over "search".
TERMS = {
    "golden set": "the answer key: questions with the known right answer",
    "golden dataset": "the answer key: questions with the known right answer",
    "golden candidate": "a live answer someone marked bad, waiting for a person to write the right answer",
    "retrieval": "finding the right section of the right policy",
    "hit@1": "the right section came back first",
    "hit@3": "the right section was in the top 3 results",
    "MRR": "a score for how high the right section ranks: 1st = 1, 2nd = 0.5, 3rd = 0.33",
    "recall@k": "share of the right sections found in the top k results",
    "hard negative": "a section that looks right but isn't",
    "hard negatives": "sections that look right but aren't",
    "LLM judge": "a second AI that grades the answers",
    "Cohen's kappa": "an agreement score that discounts lucky guesses; 1 = perfect agreement",
    "ablation": "turning off one part at a time to see what it adds",
    "CI gate": "automatic tests on every code change; a lower score blocks the change",
    "CI": "continuous integration: tests that run automatically on every code change",
    "red team": "people or scripts that try to trick the AI on purpose",
    "red-team": "people or scripts that try to trick the AI on purpose",
    "red teaming": "trying to trick the AI on purpose to find weak spots",
    "baseline": "saved scores that every new run is compared with",
    "chunk": "a small piece of a document; here, one policy rule",
    "chunks": "small pieces of a document; here, one policy rule each",
    "chunker": "the code that cuts documents into chunks",
    "embedded": "turned into numbers (a vector) so similar meanings sit close together",
    "vector": "text turned into a list of numbers so similar meanings sit close together",
    "vectors": "text turned into lists of numbers so similar meanings sit close together",
    "Chroma": "the database that stores the policy vectors",
    "BM25": "a classic keyword-search score",
    "hybrid search": "meaning search and keyword search combined",
    "Reciprocal Rank Fusion": "a simple way to merge two ranked lists into one",
    "re-ranking": "a second model reorders the top results",
    "re-ranker": "a second model that reorders the top results",
    "cross-encoder": "a model that reads the question and a text together to score the match",
    "query rewriting": "restating a question in the policy's own wording before searching",
    "RAGAS": "an open-source library that scores RAG answers",
    "faithfulness": "how much the answer sticks to its sources",
    "answer relevancy": "how well the answer addresses the question",
    "RAG": "retrieval-augmented generation: the AI looks things up before it answers",
    "LLM": "large language model: the AI that reads and writes text (here, Claude)",
    "OCR": "reading the text in a picture of a page, like a fax",
    "CPT code": "a standard code for a medical procedure",
    "CPT": "a standard code for a medical procedure",
    "prompt injection": "hidden text that tries to give the AI new orders",
    "injection": "hidden text that tries to give the AI new orders",
    "guardrails": "checks that block unsafe or off-topic input and output",
    "LangGraph": "a tool for building AI workflows step by step",
    "LangSmith": "a service that records each AI request step by step (tracing)",
    "traces": "step-by-step records of each request: what ran, how long, what it cost",
    "Pydantic": "a library that checks data fits a fixed form",
    "schema": "a fixed form the AI's answer must fit",
    "override": "the nurse decided differently from the AI's suggestion",
    "audit log": "a permanent record of who did what and when",
    "audit": "a permanent record of who did what and when",
    "tier": "the AI's suggestion: likely approve, needs review or likely deny",
    "GitHub Actions": "GitHub's service that runs tests automatically on each change",
    "held-out": "kept aside and never used for tuning, so the score is honest",
    "drift": "quality slowly getting worse over time",
    "latency": "how long it takes to respond",
    "tokens": "pieces of words the AI reads and writes; cost is per token",
    "synthetic": "made up for the demo; no real patients",
    "red flag": "a sign that something serious may be going on",
    "conservative therapy": "non-surgical treatment such as physical therapy or medicine",
    "conservative care": "non-surgical treatment such as physical therapy or medicine",
    "sentence-transformers": "a library that turns text into vectors",
    "rationale": "the written reason for a decision",
    "medical director": "the doctor who is the only one allowed to deny a request",
    "embeddings": "text turned into numbers so similar meanings sit close together",
    "Fly.io": "the cloud service that hosts the live app",
}

# More terms (2026-11-19): the steps, the eval plan, the clinical words and the tools.
TERMS.update({
    # steps of the flow
    "ingestion": "preparing documents ahead of time: cut into chunks, tagged and stored for search",
    "read the request": "reading the incoming request's pages, finding its CPT code and scanning it for tricks",
    "input guardrails": "checks that block tricks, off-topic and secret-looking input before the AI sees it",
    "output checks": "code that verifies the AI's answer, such as every quote really being in the source",
    "human decision": "the step where a nurse or medical director decides; the AI only suggests",
    "offline evals": "grading the app on the answer key before a change ships",
    "after release": "watching quality, cost and errors on the live app",
    "generation": "the AI writing the answer or review from the retrieved text",
    "query rewriting": "restating a question in the policy's own wording before searching",
    # eval words
    "evals": "graded tests of the AI's answers, scored against an answer key",
    "eval harness": "the script that runs every eval question and scores the answers",
    "answer key": "the known right answers the AI is graded against",
    "golden question": "one question in the answer key, with its known right answer",
    "golden questions": "questions in the answer key, with their known right answers",
    "golden rows": "questions in the answer key, with their known right answers",
    "gate": "an automatic check that blocks a change when scores drop",
    "threshold": "the cut-off a score must stay above",
    "regression": "a change that makes results worse than before",
    "noise": "small random differences between runs of the same test",
    "spread": "how far apart the scores of repeated runs are",
    "dev split": "practice questions used while tuning",
    "test split": "held-out questions used only for the final score",
    "LLM-as-judge": "using a second AI to grade the answers",
    "judge prompt": "the instructions given to the AI grader",
    "agreement": "how often two graders give the same grade",
    "context precision": "how much of the text the AI was given was actually useful",
    "precision@k": "share of the top k results that are right",
    "ground truth": "the known right answer",
    "hallucination": "the AI stating something that isn't in the sources",
    "grounded": "backed by the source documents",
    "feedback loop": "turning real mistakes into new test questions so they stay fixed",
    "thumbs up/down": "a quick good or bad rating a user gives an AI answer",
    "thumbs down": "a user marking an AI answer as bad",
    "thumbs-down": "a user marking an AI answer as bad",
    "override rate": "how often people decide differently from the AI's suggestion",
    "quote verification": "code checking that every quote really appears in the source PDF",
    "quote-verified rate": "share of the AI's quotes found word for word in the sources",
    "citation": "a pointer to the exact page and quote that supports a claim",
    "citations": "pointers to the exact page and quote that support each claim",
    "ablation table": "a table of scores with one part turned off at a time",
    "mock": "a fake stand-in used in tests so no real AI call is made",
    "mocked": "using fake stand-ins instead of real AI calls in tests",
    "live": "using the real Claude API (costs money), not a fake stand-in",
    "unit tests": "small automatic tests of one piece of code",
    "monitoring": "watching the live app's quality, cost and errors",
    "observability": "being able to see what the live app is doing and why",
    "tracing": "recording each request step by step",
    "alerts": "warnings raised when a quality or cost number crosses a limit",
    # search and RAG words
    "embedding": "text turned into numbers so similar meanings sit close together",
    "meaning search": "search by meaning using vectors, not exact words",
    "keyword search": "search for the exact words in the question",
    "semantic chunking": "cutting text where the meaning changes",
    "structure-aware": "cutting a document at its own sections and rules",
    "clause-aware chunking": "cutting a policy at each clause so every piece is one whole rule",
    "fixed-size": "cutting text every N characters, wherever that lands",
    "recursive character split": "cutting long text by paragraph, then line, then sentence",
    "overlap": "characters repeated between neighboring chunks so nothing is lost at a cut",
    "contextual header": "a line on each chunk naming its policy, version, section and page",
    "metadata": "labels stored with each chunk: policy, CPT, version, section, page",
    "index": "the searchable store of chunks and their vectors",
    "re-index": "rebuild the searchable store after documents change",
    "clause": "one rule in a policy, such as §2.A",
    "pipeline": "the series of steps a request goes through",
    "workflow": "a fixed series of steps the app runs",
    "agent": "an AI that chooses which tools to use to answer",
    "tool": "a function the AI can call, such as policy search",
    "prompt": "the instructions and text given to the AI",
    "system prompt": "the standing instructions that set the AI's rules and role",
    "JSON": "a simple text format for structured data",
    "Claude": "Anthropic's AI model that this app uses",
    "AI Assist": "the app's chat helper for staff questions",
    "intent gate": "a check that turns away questions that aren't about prior authorization",
    "off-topic": "not about prior authorization",
    "PII": "personal details that identify someone, like a name or date of birth",
    "PHI": "protected health information: real patient data",
    "GitHub secret": "a password or key stored safely in GitHub for automated runs",
    "API key": "a secret code that lets the app use a paid service",
    "deploy": "put a new version of the app live",
    "RapidOCR": "an OCR library that runs on this computer, so nothing leaves it",
    "reportlab": "a library that creates PDFs",
    "pypdf": "a library that reads text from PDFs",
    "pytest": "the standard Python testing tool",
    "scikit-learn": "a Python library for statistics and machine learning",
    "Typer": "a library for building command-line tools",
    # prior authorization and clinical words
    "prior authorization": "a health plan approving a test or treatment before it happens",
    "health plan": "the insurer that pays for members' care",
    "member": "a person covered by the health plan",
    "provider": "the doctor or clinic asking for the test",
    "coverage policy": "the health plan's rules for when a test is covered",
    "policy": "the health plan's written rules for when a test is covered",
    "policies": "the health plan's written rules for when tests are covered",
    "medical necessity": "whether a test is truly needed under the policy's rules",
    "adverse determination": "a denial; only a medical director may issue one",
    "peer-to-peer": "a call between the ordering doctor and the medical director about a denial",
    "appeal": "a formal request to reverse a denial",
    "expedited review": "a fast review, within 72 hours, when waiting could harm the member",
    "turnaround": "how long a request takes from arrival to decision",
    "rework": "a request sent back because information was missing",
    "intake": "receiving a request and creating its case",
    "completeness": "whether every required document is present",
    "needs review": "the AI's middle suggestion: a person should look closely",
    "likely approve": "the AI's suggestion that the criteria look met",
    "likely deny": "the AI's suggestion that the criteria look unmet; only a medical director can deny",
    "Incomplete": "case status: documents are missing",
    "pend": "pause a case for more information or a medical director",
    "nurse": "the reviewer who checks requests; can approve or pend, not deny",
    "MRI": "a scan that uses magnets to show soft tissue like discs, ligaments and the brain",
    "CT": "a fast X-ray scan, often used first to look for bleeding",
    "X-ray": "a quick image that shows bones",
    "physical therapy": "guided exercise treatment",
    "PT": "physical therapy: guided exercise treatment",
    "PT records": "notes from physical therapy visits with dates and results",
    "NSAIDs": "anti-inflammatory pain medicines such as ibuprofen",
    "lumbar": "the lower back",
    "radicular": "nerve pain that travels down the leg",
    "cauda equina syndrome": "an emergency where nerves at the base of the spine are squeezed",
    "saddle numbness": "numbness around the groin and buttocks, a warning sign",
    "epidural steroid injection": "a back injection of anti-inflammatory medicine",
    "meniscus": "the cushion cartilage inside the knee",
    "ligament": "tissue that holds joints together",
    "ACL": "a key ligament inside the knee",
    "McMurray": "a knee exam test for a meniscus tear",
    "Lachman": "a knee exam test for an ACL tear",
    "osteoarthritis": "wear-and-tear arthritis",
    "osteochondritis dissecans": "a joint problem in young people where bone under cartilage loosens",
    "mechanical symptoms": "the knee locking, catching or giving way",
    "migraine": "a common type of severe headache",
    "multiple sclerosis": "a disease that damages nerve coverings in the brain and spine",
    "papilledema": "swelling at the back of the eye from pressure in the skull",
    "contrast": "dye given during a scan to show some tissues better",
    "gadolinium": "the contrast dye used in MRI",
    "sedation": "medicine to help someone stay calm and still",
    "MRI-conditional": "an implant that is safe in MRI under set conditions",
    "aneurysm clip": "a metal clip placed on a weak blood vessel in the brain",
    "pacemaker": "an implanted device that keeps the heart beating regularly",
    "ICD-10": "a standard code for a diagnosis",
    "NPI": "a provider's national ID number",
    # platform war stories (war-stories-platform.md)
    "service layer": "the one place in the code where all the business rules live",
    "thin client": "a screen or tool that only calls the service layer and holds no rules",
    "unverified-quote rate": "how often the AI's quote can't be found in the source document",
    "cost cap": "a spending limit on AI calls, per case, per user or per day",
    "graceful degradation": "keep working safely when part of the system fails",
    "LLM gateway": "one shared front door for all AI model calls: budgets, caching, routing, failover",
    "showback": "showing each team what it spent, without billing it",
    "platform thinking": "building shared tools every team uses, instead of one-off apps",
    "MCP": "Model Context Protocol: a standard plug that lets AI assistants use an app's tools",
    "Claude Cowork": "Anthropic's assistant that can run scheduled jobs using connected tools",
    "least privilege": "give each user or agent only the access it needs, nothing more",
    "bearer token": "a secret key sent with each request to prove it's allowed",
    "state machine": "a rule list of which status changes are allowed",
    "RBAC": "role-based access control: what you can do depends on your role",
    "checkpointed": "saved step by step, so it can resume after a restart",
    "prompt-cached": "the unchanged start of a prompt is reused cheaply instead of re-read",
    "rate limit": "a cap on how many requests a user can make per minute",
    "fallback model": "a backup AI model used when the main one is down or overloaded",
    "contract test": "a test that a service still works the way its docs and clients expect",
    "Docker": "packages the app so it runs the same anywhere",
    "SLOs": "reliability targets, like 99.9% uptime",
    "runbook": "a step-by-step guide for handling a known problem",
    "BAA": "the HIPAA contract with a vendor that touches patient data",
    "load test": "sending many requests at once to see if the app holds up",
    # ServiceApps setting (war-stories.md)
    "ServiceApps": "our name for a large enterprise workflow platform for IT, HR and customer service",
    "KB article": "one page in the knowledge base: a how-to, policy or fix",
    "knowledge base": "the company's library of how-to and policy articles",
    "incident": "a ticket saying something is broken",
    "change request": "a ticket asking to change a system, which needs approval first",
    "change advisory board": "the group that approves risky changes to systems",
    "reassignment": "a ticket bounced from one team to another",
    "assignment group": "the team a ticket is routed to",
})

SKIP_TAGS = {"a", "code", "pre", "h1", "h2", "h3", "h4", "th", "script", "style"}
BLOCK_TAGS = {"p", "li", "td"}
GLOSSARY_SKIP_ID = "words-used-in-this-post"     # the plain-words table at the top explains terms itself
GLOSSARY_ID = "key-terms"

NO_PLURAL = {"overlap"}   # "the wording overlaps the rules" is not chunk overlap
_PAT = _CANON = None


def rebuild() -> None:
    """(Re)compile the term matcher; call after changing TERMS or NO_PLURAL."""
    global _PAT, _CANON
    _PAT = re.compile("|".join(
        rf"(?<![\w@-]){re.escape(t)}{'' if t in NO_PLURAL else '(?:e?s)?'}(?![\w@-])"
        for t in sorted(TERMS, key=len, reverse=True)), re.I)
    _CANON = {t.lower(): t for t in TERMS}


rebuild()


def _canon(word: str) -> str | None:
    w = word.lower()
    for cand in (w, w[:-1] if w.endswith("s") else None, w[:-2] if w.endswith("es") else None):
        if cand and cand in _CANON:
            return _CANON[cand]
    return None


def slug(t: str) -> str:
    return "g-" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def add_terms(body: str) -> tuple[str, dict]:
    """Link EVERY use of a term (highlight + hover + hidden "(definition)"); each use gets its own id so
    the glossary can link back. Returns (body, {term: [(use_id, section_id, section_title), ...]})."""
    out, stack, uses = [], [], {}
    skip_section = False
    section = ("", "")
    n = 0
    parts = re.split(r"(<[^>]+>)", body)
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", part)
            if m:
                closing, tag, attrs = m.group(1) == "/", m.group(2).lower(), m.group(3)
                if tag in ("h2", "h3") and not closing:
                    hid = re.search(r'id="([^"]+)"', attrs)
                    title = re.sub(r"<[^>]+>", "", parts[i + 1]) if i + 1 < len(parts) else ""
                    section = (hid.group(1) if hid else "", html.unescape(title))
                    if tag == "h2":
                        skip_section = False   # the plain-words table gets hover too (Mike, 2026-11-19)
                if not closing and not part.endswith("/>"):
                    stack.append(tag)
                elif closing and tag in stack:
                    while stack and stack.pop() != tag:
                        pass
            out.append(part)
        elif part.strip() and not skip_section and not (set(stack) & SKIP_TAGS) and (set(stack) & BLOCK_TAGS):
            def rep(mm):
                nonlocal n
                word = mm.group(0)
                term = _canon(word)
                if term is None:
                    return word
                n += 1
                uid = f"u{n}"
                uses.setdefault(term, []).append((uid, section[0], section[1]))
                d = html.escape(TERMS[term])
                return (f'<a class="term" id="{uid}" href="#{slug(term)}" data-tip="{d}">{word}</a>'
                        f'<span class="def"> ({d})</span>')
            out.append(_PAT.sub(rep, part))
        else:
            out.append(part)
        i += 1
    return "".join(out), uses


def glossary(uses: dict) -> str:
    """Key terms at the end: one entry per term used, with 'Used in' links back to each section."""
    rows = []
    for term in sorted(uses, key=str.lower):
        seen, links = set(), []
        for uid, sid, title in uses[term]:
            if sid and sid not in seen:
                seen.add(sid)
                links.append(f'<a href="#{uid}">{html.escape(title)}</a>')
        rows.append(f'<div class="entry" id="{slug(term)}"><dt>{html.escape(term)}</dt>'
                    f'<dd>{html.escape(TERMS[term][0].upper() + TERMS[term][1:])}.'
                    f'<span class="used">Used in: {", ".join(links)}</span>'
                    f'<a class="back" href="#" data-back>↩ Back to where you were</a></dd></div>')
    return (f'<h2 id="{GLOSSARY_ID}">Key terms</h2><p>Every highlighted word in this post links here. '
            f'Click <b>↩ Back</b> to return to the spot you came from.</p><dl class="glossary">'
            + "".join(rows) + "</dl>")


CSS = """
:root{--hl:#e4f1ee}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--hl:#1d3531}}
:root[data-theme="dark"]{--hl:#1d3531}
a.term{color:inherit;background:var(--hl);border-radius:3px;padding:0 2px;text-decoration:underline dotted var(--accent);text-underline-offset:3px;scroll-margin-top:40vh}
a.term:hover{color:var(--accent)}
a.sec{text-decoration:underline dotted;text-underline-offset:3px}
a.term.here{outline:2px solid var(--accent)}
.def{color:var(--muted);font-size:.9em}
html:not(.show-defs) .def{display:none}
.term-tip{position:absolute;z-index:50;max-width:320px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:10px 12px;font-size:.88rem;line-height:1.45;box-shadow:0 6px 20px rgba(0,0,0,.18)}
.term-tip strong{display:block;color:var(--accent);margin-bottom:2px}
.defs-toggle{font-size:.85em;margin:0 0 16px}
dl.glossary .entry{padding:10px 0;border-bottom:1px solid var(--line);scroll-margin-top:12px}
dl.glossary .entry:target{background:var(--hl)}
dl.glossary dt{font-weight:650}dl.glossary dd{margin:2px 0 0}
dl.glossary .used{display:block;color:var(--muted);font-size:.88em;margin-top:4px}
dl.glossary .back{display:inline-block;font-size:.88em;margin-top:4px}
"""

HEAD_JS = ("<script>(function(){var q=new URLSearchParams(location.search).get('defs');"
           "if(q&&/^(1|y|yes|on|true|show)$/i.test(q))document.documentElement.classList.add('show-defs');})();</script>")

TOGGLE = ('<p class="defs-toggle"><a href="#" id="defs-toggle">Show definitions in ( )</a> · '
          'hover a highlighted word for its meaning, click it for details · '
          'open with <code>?defs=1</code> to show definitions</p>')

TAIL_JS = """<script>
(function(){
  var r=document.documentElement, b=document.getElementById('defs-toggle'), last=null;
  function paint(){ if(b) b.textContent=r.classList.contains('show-defs')?'Hide definitions in ( )':'Show definitions in ( )'; }
  if(b) b.addEventListener('click',function(e){ e.preventDefault(); r.classList.toggle('show-defs');
    var u=new URL(location.href); u.searchParams.set('defs', r.classList.contains('show-defs')?'1':'0');
    history.replaceState(null,'',u); paint(); });
  paint();
  /* click a term -> its glossary entry; "Back" -> the exact term you clicked */
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a.term'); if(a){ last=a.id; return; }
    var k=e.target.closest&&e.target.closest('a[data-back]'); if(!k) return;
    e.preventDefault();
    var id=last||(history.state&&history.state.from);
    if(id){ var t=document.getElementById(id); location.hash=id; document.querySelectorAll('a.term.here').forEach(function(x){x.classList.remove('here');});
      if(t){ t.classList.add('here'); setTimeout(function(){t.classList.remove('here');},2500);} }
    else history.back();
  });
  var tip=document.createElement('div'); tip.className='term-tip'; tip.setAttribute('role','tooltip'); tip.hidden=true; document.body.appendChild(tip);
  function show(a){ var d=a.getAttribute('data-tip'); if(!d) return;
    tip.innerHTML=''; var h=document.createElement('strong'); h.textContent=a.textContent; tip.appendChild(h); tip.appendChild(document.createTextNode(d));
    tip.hidden=false; var rc=a.getBoundingClientRect(), w=tip.offsetWidth,
      x=Math.min(Math.max(8,rc.left+window.scrollX), window.scrollX+document.documentElement.clientWidth-w-8),
      y=rc.bottom+window.scrollY+6; if(rc.bottom+tip.offsetHeight+12>window.innerHeight) y=rc.top+window.scrollY-tip.offsetHeight-6;
    tip.style.left=x+'px'; tip.style.top=y+'px'; }
  function hide(){ tip.hidden=true; }
  document.addEventListener('mouseover',function(e){ var a=e.target.closest&&e.target.closest('a.term, a.sec'); if(a) show(a); });
  document.addEventListener('mouseout',function(e){ var a=e.target.closest&&e.target.closest('a.term, a.sec'); if(a&&!a.contains(e.relatedTarget)) hide(); });
  document.addEventListener('focusin',function(e){ if(e.target.matches&&e.target.matches('a.term, a.sec')) show(e.target); });
  document.addEventListener('focusout',hide); window.addEventListener('scroll',hide,{passive:true}); window.addEventListener('hashchange',hide);
})();
</script>"""


def section_tips(body: str) -> str:
    """Links to a section (step names, plan parts, checklist rows, reading list) get a hover box with that
    section's description: the 'What it does.' paragraph for steps, otherwise the first paragraph."""
    tips = {}
    for m in re.finditer(r'<h([23]) id="([^"]+)">(.*?)</h\1>(.*?)(?=<h[23] |$)', body, re.S):
        sid, block = m.group(2), m.group(4)
        paras = re.findall(r"<p>(.*?)</p>", block, re.S)
        what = next((p for p in paras if p.startswith("<b>What it does.</b>")), None)
        text = what or next((p for p in paras if not p.startswith("<a ")), "")
        text = re.sub(r'<span class="def">.*?</span>', "", text)
        text = html.unescape(re.sub(r"<[^>]+>", "", text)).replace("What it does.", "").strip()
        if text:
            tips[sid] = text if len(text) <= 220 else text[:217].rsplit(" ", 1)[0] + "…"

    def rep(m):
        sid, label = m.group(1), m.group(2)
        if sid not in tips or label.startswith(("↑", "↩")):
            return m.group(0)
        return f'<a class="sec" href="#{sid}" data-tip="{html.escape(tips[sid])}">{label}</a>'
    return re.sub(r'<a href="#([^"]+)">(.*?)</a>', rep, body)


def term_link_tips(body: str) -> str:
    """A link whose text is exactly a key term (e.g. a book solution linking to its deep dive) gets that term's
    meaning as a hover box, like a section link. Links that already have a class are left alone."""
    lower = {k.lower(): v for k, v in TERMS.items()}

    def rep(m):
        href, rest, label = m.group(1), m.group(2), m.group(3)
        tip = lower.get(html.unescape(re.sub(r"<[^>]+>", "", label)).strip().lower())
        if not tip:
            return m.group(0)
        tip = tip[0].upper() + tip[1:]
        return f'<a class="sec" href="{href}"{rest} data-tip="{html.escape(tip)}">{label}</a>'
    return re.sub(r'<a href="([^"]+)"((?: target="_blank" rel="noopener")?)>(.*?)</a>', rep, body)


def new_tab_links(body: str) -> str:
    """Links that leave the page (other pages, files, websites) open in a new tab; #anchors stay in the same tab."""
    return re.sub(r'<a href="(?!#)([^"]+)"(?![^>]*\btarget=)', r'<a href="\1" target="_blank" rel="noopener"', body)


def apply(body: str, css: str) -> tuple[str, str, str, str]:
    """-> (body with linked terms, toggle after the byline and Key terms glossary at the end, css, head js, tail js)."""
    body = new_tab_links(body)
    body, uses = add_terms(body)
    body = section_tips(body)
    body = term_link_tips(body)
    i = body.find("</p>", body.find("</h1>"))
    if i >= 0:
        body = body[:i + 4] + TOGGLE + body[i + 4:]
    return body + glossary(uses), css + CSS, HEAD_JS, TAIL_JS
