# Deep dive 1 of 12: Ingestion, turning policy PDFs into searchable rules

Nov 19, 2026 · Michael Chang · Live demo: nurseops-now.fly.dev · Status: built; clause-vs-fixed score not measured yet

**Part of:** [Proving the answers are good: the NurseOps Now eval plan](../nurseops-now-evals.html), [Step 1: Ingestion](../nurseops-now-evals.html#step-1-ingestion) · Next: Deep dive 2, Read the request (to come)

**Read in this order**

1. [Why this post](#why-this-post): what this deep dive covers, and how cutting by structure differs from cutting by characters
2. [ServiceApps example](#serviceapps-example-the-same-ingestion-for-kb-articles): the same ingestion for tech and domain KB articles, with 5 interview answers (yellow box)
3. [Why we ingest this way](#why-we-ingest-this-way): the problem, the choice, and what goes wrong without it (no code), with [a color picture of the real policy cut two ways](#see-it-one-policy-cut-two-ways)
4. [Words used in this post](#words-used-in-this-post): the terms
5. [How ingestion flows](#how-ingestion-flows): the 8 sub-steps in the order the code runs them
6. [Sub-step details](#sub-step-details-one-policy-all-the-way-through): the real code and real output for each one
7. [Try it yourself](#try-it-yourself): commands to run it on your machine
8. [How it's tested](#how-it-s-tested): the unit tests and today's result
9. [Checklist](#checklist-what-is-done-and-what-is-next) and [Honest gaps](#honest-gaps): what is done, and what isn't measured or isn't true yet
10. [Interview answer](#interview-answer) and [What this proves](#what-this-proves)

## Why this post

The [eval plan](../nurseops-now-evals.html) follows one question through 12 steps. Each step got a few paragraphs there. This series gives each step its own post with the real code, so a reader can see exactly how it works, not just what it does.

Ingestion comes first because every later step depends on it. Search can only find what ingestion stored, and the AI can only quote what search found. If a rule is cut in half here, no later step can put it back together.

**How this differs from cutting by characters.** The usual way is to count characters: cut every 500, wherever that lands. It is fast and works on any text, but it doesn't know what a rule is. It cuts mid-rule and even mid-word, and it glues the end of one rule to the start of the next. NurseOps Now turns this around: **the policy's structure decides where to cut, and characters only set a size limit.**

**How we break it up, in order of priority:**

1. **Structure first: sections and rules.** Cut at every numbered section ("3. Required documentation") and every lettered rule ("A. Suspected meniscus…"). The policy's author already decided where one rule ends, so we use their boundaries. One chunk is one complete rule.
2. **Context carried down.** Each lettered rule keeps the title of its section ("Covered when ONE of the following is documented") and gets a header with the policy, version, CPT code and page. A small rule still says whose rule it is and what it means when read alone.
3. **Characters second, only as a safety net.** Only if one rule is longer than 1,200 characters is it split again. Even then it tries natural breaks first (paragraph, then line, then sentence), repeats the last 150 characters at the start of the next piece, and only cuts at a raw character count if there is no break at all.

**Why characters are the backup and not the main rule:**

- **The limit comes from the model, not the policy.** The embedding model (all-MiniLM-L6-v2) reads at most 256 word-pieces, about 1,000–1,200 characters, and silently ignores the rest. A rule longer than that would be only partly embedded, and its end could never be found. So characters cap the size, but they never pick the boundary.
- **Splitting at a break beats splitting at a count.** When a split is needed, a paragraph or sentence break keeps whole thoughts together, and the overlap means a sentence crossing the cut appears whole in at least one piece.
- **Today the safety net never fires.** The longest of the 83 chunks is 487 characters, so every chunk in the index is exactly one rule. The net is there for a future policy with a very long rule.

**What we added to this idea:**

- **There is no minimum size.** Character-based chunking usually also merges small pieces to reach a target size. We don't: the shortest rule (§2.D _Planning for knee surgery_, 132 characters with its header) stays its own chunk. Merging it into its neighbor would mix two rules, and the AI could cite the wrong one. The header gives a short chunk the context its body lacks.
- **No overlap between rules.** Character chunking repeats text between neighboring pieces (often 10–20%) to patch cuts that land mid-sentence. Our cuts land where a rule ends, so there is nothing to patch, and the chunks don't overlap at all. Adding overlap here would do harm: the end of §2.A would appear inside §2.B's chunk, so a search could return §2.B for a question about §2.A, and the AI could cite the wrong section. The only overlap is the 150 characters between pieces of **one** long rule when the fallback splits it, and it never crosses into another rule.
- **The cut decides what can be cited.** The AI must quote a rule and give its § and page, and a later step matches every quote against the PDF. With character cuts, a chunk could start in §2.A and end in §2.B, so no single § or page would be true for it. With structure cuts, every chunk has exactly one § and one page.

**In plain terms:** before a librarian can answer questions, someone has to put the books on the shelves, with labels. This post is about that someone.

:::highlight
## ServiceApps example: the same ingestion for KB articles

**If someone asks "how would you do this over a ServiceApps knowledge base?"**, this is the answer. The 8 sub-steps of this post stay the same, and only the source changes: PDF files become KB articles in the `kb_knowledge` table. The strategy is the same: **the article's own structure decides where to cut** (its headings, numbered steps and table rows), **and characters are only a size limit** for a section that is too long.

_Illustrative example: no ServiceApps instance is connected to NurseOps Now, so the two articles below are made up to show the pattern. The API part of the sketch has never been run; the chunking part was run on the two made-up articles to draw the picture._

**Two kinds of article, two kinds of "unit"**

| | Tech / software article | Domain article |
|---|---|---|
| Example | KB0010234 _Connect to the company VPN on macOS_ (KB: IT Software, Category: Network › VPN) | KB0020311 _Remote work policy_ (KB: HR Policies, Category: Workplace) |
| Written as | Symptoms, Applies to, numbered Steps, an error-code table, Related articles | Numbered rules (eligibility, equipment, working abroad, approvals), each with its exceptions |
| One chunk = | One heading section. The numbered steps stay together as one chunk, and each error-code row becomes its own chunk | One numbered rule, with its exceptions kept in the same chunk |
| A question it answers | "VPN says error 809, what do I do?" | "Can I work from another country for three weeks?" |
| What goes wrong with fixed-size cuts | Steps 1–4 land in one chunk and steps 5–6 in the next, so the answer stops halfway through the fix | The rule "up to 10 working days a year" lands in one chunk and "longer stays need HR and Payroll approval" in the next, so the answer says _no_ when the real answer is _yes, with approval_ |

**The 8 sub-steps, side by side**

| # | Sub-step | NurseOps Now (PDF files) | ServiceApps (KB articles) |
|---|---|---|---|
| 1 | Find the source | `policies/index.json` lists each file, number and version | REST Table API on `kb_knowledge`: only `workflow_state=published`, filtered by knowledge base |
| 2 | Read the content | pypdf; drop page furniture | Article body is HTML in the `text` field; strip tags and drop template boilerplate (banners, "Was this helpful?", attachment lists) |
| 3 | Find the units | Numbered sections and lettered rules | `<h2>`/`<h3>` headings from the article template; keep a numbered list whole; one chunk per row of an error-code table |
| 4 | Header + metadata | Document number, version, section and page | KB number, knowledge base, category, title and section heading; metadata adds `sys_id`, `sys_updated_on` and who can read it (user criteria) |
| 5 | Split long sections | 1,200-character fallback at natural breaks | Same; long troubleshooting sections are common |
| 6 | Flag injection | Pattern check on the text | Same, and it matters more: many people can edit KB articles. Also mask personal data pasted in from incidents (names, emails, phone numbers) |
| 7 | Embed | all-MiniLM-L6-v2, local | Same model, or a larger one for thousands of articles |
| 8 | Store | Delete the document's old chunks, then add | Delete by article `sys_id`, then add; remove retired articles; **re-embed only articles whose content hash changed**; filter search results by what the user may read |

**Sketch: pull, hash and chunk KB articles** (Python standard library, plus `requests` for the API call; saved as `tools/scripts/kb_chunk_sketch.py`)

```python
import hashlib
from html.parser import HTMLParser

FIELDS = "sys_id,number,short_description,text,kb_knowledge_base,kb_category,sys_updated_on,can_read_user_criteria"
SKIP_CLASSES = {"kb-banner", "kb-feedback"}      # template boilerplate, not content
SKIP_SECTIONS = {"Related articles"}             # links only: no answer in them


def fetch_published(instance: str, auth, kb_sys_id: str):
    """Page through published articles in one knowledge base (REST Table API)."""
    import requests
    url = f"https://{instance}.serviceapps.com/api/now/table/kb_knowledge"
    offset = 0
    while True:
        r = requests.get(url, auth=auth, timeout=30, headers={"Accept": "application/json"}, params={
            "sysparm_query": f"workflow_state=published^kb_knowledge_base={kb_sys_id}",
            "sysparm_fields": FIELDS, "sysparm_display_value": "all",   # value + display_value per field
            "sysparm_limit": 100, "sysparm_offset": offset})
        r.raise_for_status()
        rows = r.json()["result"]
        if not rows:
            return
        yield from rows
        offset += len(rows)


def content_hash(a) -> str:
    """Fingerprint of the article body: re-embed only when this changes."""
    return hashlib.sha256(a["text"]["value"].encode()).hexdigest()


class Blocks(HTMLParser):
    """Flatten article HTML into blocks: ("heading", t), ("line", t), ("row", cells, is_header), ("skip", t)."""

    def __init__(self):
        super().__init__()
        self.blocks, self.text, self.cells, self.skip, self.lists = [], [], [], None, []

    def handle_starttag(self, tag, attrs):
        if self.skip is None and dict(attrs).get("class") in SKIP_CLASSES:
            self.skip = tag
        if tag in ("ol", "ul"):
            self.lists.append([tag, 0])
        if tag == "tr":
            self.cells, self.header_row = [], False
        if tag == "th":
            self.header_row = True
        if tag in ("h2", "h3", "p", "li", "td", "th") or tag == self.skip:
            self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_endtag(self, tag):
        t = " ".join("".join(self.text).split())
        if tag == self.skip:
            self.blocks.append(("skip", t))
            self.skip = None
        elif self.skip:
            return
        elif tag in ("ol", "ul"):
            self.lists.pop()
        elif tag in ("td", "th"):
            self.cells.append(t)
        elif tag == "tr":
            self.blocks.append(("row", self.cells, self.header_row))
        elif tag in ("h2", "h3"):
            self.blocks.append(("heading", t))
        elif tag == "li":
            kind = self.lists[-1] if self.lists else ["ul", 0]
            kind[1] += 1
            self.blocks.append(("line", f"{kind[1]}. {t}" if kind[0] == "ol" else f"- {t}"))
        elif tag == "p":
            self.blocks.append(("line", t))


def units(html: str) -> list[tuple[str, list[str]]]:
    """(heading, lines) per chunk: one per heading section, one per table row; numbered steps stay together."""
    p = Blocks()
    p.feed(html)
    out, heading = [], "Overview"
    for b in p.blocks:
        if b[0] == "heading":
            heading = b[1]
            out.append((heading, []))
        elif heading in SKIP_SECTIONS or b[0] == "skip":
            continue
        elif b[0] == "line":
            if not out:
                out.append((heading, []))
            out[-1][1].append(b[1])
        elif b[0] == "row" and not b[2]:                   # one chunk per row, named by its first cell
            out.append((b[1][0], [" ".join(b[1][1:])]))
    return [(h, lines) for h, lines in out if lines]       # a heading with no text of its own isn't a chunk


def chunk_article(a) -> list[dict]:
    """One chunk per section or table row, each with a header naming the article: the KB version of 'one per clause'."""
    num, title = a["number"]["value"], a["short_description"]["value"]
    kb, cat = a["kb_knowledge_base"]["display_value"], a["kb_category"]["display_value"]
    return [{"id": f"{num}-{n}",
             "text": f"[{num} | {kb} | {cat} | {title} | {h}]\n" + "\n".join(lines),
             "meta": {"sys_id": a["sys_id"]["value"], "number": num, "kb": kb, "category": cat,
                      "section": h, "updated": a["sys_updated_on"]["value"],
                      "can_read": a["can_read_user_criteria"]["value"]}}
            for n, (h, lines) in enumerate(units(a["text"]["value"]))]
```

Then [sub-steps 5–8](#how-ingestion-flows) run unchanged: the long-section fallback, the injection check, embed, and Chroma. The one change is in sub-step 8: skip an article when its `content_hash()` matches the stored one, and delete chunks `where={"sys_id": ...}` before adding new ones.

**See two whole articles and all their chunks** (illustrative). These are the two made-up articles above, each shown whole, run through `chunk_article()` from the sketch. Each colored box is one chunk, the bold `[…]` line is the header the code adds, struck-through lines are thrown away, and italic headings move into the header.

:::html
<div class="cv">
<style>
.cv{margin:16px 0;font-size:.92em}.cv h4{margin:18px 0 6px}.cv .note{color:var(--muted);font-size:.9em;margin:4px 0 10px}
.cv .doc{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--bg)}
.cv .ln{display:block;font-family:ui-monospace,Menlo,monospace;font-size:.85em;white-space:pre-wrap;line-height:1.45;margin:0}
.cv .skip{color:var(--muted);text-decoration:line-through;opacity:.75}
.cv .tag{display:inline-block;font:600 .75em/1.6 -apple-system,system-ui,sans-serif;border-radius:10px;padding:0 8px;color:#fff;margin:0 0 4px}
.cv .ck{border-left:5px solid var(--h);background:color-mix(in srgb,var(--h) 13%,transparent);border-radius:6px;padding:6px 10px;margin:8px 0}
.cv .hdr{font-family:ui-monospace,Menlo,monospace;font-size:.8em;color:var(--h);font-weight:600;white-space:pre-wrap;margin:0 0 2px}
.cv .gone{border:1px dashed var(--line);border-radius:6px;padding:4px 10px;margin:8px 0}
.cv .cut{display:inline-block;background:#e03131;color:#fff;font-weight:700;border-radius:4px;padding:0 4px;margin:0 2px;font-family:-apple-system,system-ui,sans-serif}
.cv .page{border:1px solid var(--line);border-radius:8px;padding:8px 12px 4px;margin:12px 0;background:var(--bg)}.cv .pno{font:600 .8em/1.4 -apple-system,system-ui,sans-serif;color:var(--muted);margin:0 0 6px}.cv .title{opacity:.7;font-style:italic}.cv .key{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.85em;margin:6px 0 4px}.cv .key span{white-space:nowrap}
.cv .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:4px}
</style>
<h4>Article 1 (tech / software): KB0010234 Connect to the company VPN on macOS → 6 chunks</h4>
<div class="page"><div class="pno">KB0010234 · KB: IT Software · Category: Network › VPN · Published</div>
<div class="ln skip">Internal: do not share outside the company.</div>
<div class="ck" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 1 of 6 · Symptoms · 163 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Symptoms]</div>
<div class="ln title">Symptoms   ← heading, goes into the header</div>
<div class="ln">The VPN client won&#x27;t connect, or connects and drops after a few seconds.</div>
</div>
<div class="ck" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 2 of 6 · Applies to · 138 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Applies to]</div>
<div class="ln title">Applies to   ← heading, goes into the header</div>
<div class="ln">- macOS 14 and later</div>
<div class="ln">- Company VPN client 6.x</div>
</div>
<div class="ck" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 3 of 6 · Steps · 378 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Steps]</div>
<div class="ln title">Steps   ← heading, goes into the header</div>
<div class="ln">1. Open the VPN client from the menu bar.</div>
<div class="ln">2. Enter the portal address vpn.example.com.</div>
<div class="ln">3. Sign in with your company account and approve the MFA prompt.</div>
<div class="ln">4. Wait until the status shows Connected.</div>
<div class="ln">5. If it fails, quit the client and sign in again.</div>
<div class="ln">6. Still failing: find your error code below.</div>
</div>
<div class="gone"><div class="ln">Error codes</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: each table row below is its own chunk, named by its first cell</div></div>
<div class="ln title">Code | Meaning and fix   ← table header row, not a chunk</div>
<div class="ck" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 4 of 6 · Error 809 · 306 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Error 809]</div>
<div class="ln">Error 809 | Error 809 means the VPN can&#x27;t reach the server. Check that you are not on a guest Wi-Fi network, then restart the VPN client. If it continues, open an incident with category Network › VPN and attach the client log.</div>
</div>
<div class="ck" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 5 of 6 · Error 812 · 196 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Error 812]</div>
<div class="ln">Error 812 | Error 812 means your account isn&#x27;t in the VPN access group. Request &quot;VPN access&quot; in the service catalog.</div>
</div>
<div class="ck" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 6 of 6 · Error 619 · 186 chars</span><div class="hdr">[KB0010234 | IT Software | Network › VPN | Connect to the company VPN on macOS | Error 619]</div>
<div class="ln">Error 619 | Error 619 means the connection timed out. Switch networks or restart your Mac, then try again.</div>
</div>
<div class="ln skip">Related articles</div>
<div class="ln skip">- KB0010199 Reset your MFA device</div>
<div class="ln skip">- KB0010240 Connect to the VPN on Windows</div>
<div class="ln skip">Was this article helpful? Yes / No</div>
</div>
<h4>Article 2 (domain: HR policy): KB0020311 Remote work policy → 6 chunks</h4>
<div class="page"><div class="pno">KB0020311 · KB: HR Policies · Category: Workplace · Published</div>
<div class="ln skip">Internal: do not share outside the company.</div>
<div class="ck" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 1 of 6 · 1. Purpose · 126 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 1. Purpose]</div>
<div class="ln title">1. Purpose   ← heading, goes into the header</div>
<div class="ln">Sets out when employees may work away from the office.</div>
</div>
<div class="ck" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 2 of 6 · 2. Eligibility · 243 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 2. Eligibility]</div>
<div class="ln title">2. Eligibility   ← heading, goes into the header</div>
<div class="ln">Employees who have passed their probation period may work remotely up to 3 days a week, with their manager&#x27;s agreement. Roles that need on-site equipment are excluded.</div>
</div>
<div class="ck" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 3 of 6 · 3. Equipment and security · 191 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 3. Equipment and security]</div>
<div class="ln title">3. Equipment and security   ← heading, goes into the header</div>
<div class="ln">Use a company laptop and connect through the company VPN. Do not work from public Wi-Fi without the VPN.</div>
</div>
<div class="ck" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 4 of 6 · 4. Working from another country · 267 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 4. Working from another country]</div>
<div class="ln title">4. Working from another country   ← heading, goes into the header</div>
<div class="ln">Employees may work from another country for up to 10 working days a year. Longer stays need written approval from HR and Payroll before travel, because of tax and visa rules.</div>
</div>
<div class="ck" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 5 of 6 · 5. Expenses · 189 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 5. Expenses]</div>
<div class="ln title">5. Expenses   ← heading, goes into the header</div>
<div class="ln">Home internet and furniture are not reimbursed. A one-time equipment allowance is available; see the expense policy.</div>
</div>
<div class="ck" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 6 of 6 · 6. Requesting an exception · 185 chars</span><div class="hdr">[KB0020311 | HR Policies | Workplace | Remote work policy | 6. Requesting an exception]</div>
<div class="ln title">6. Requesting an exception   ← heading, goes into the header</div>
<div class="ln">Submit an &quot;HR exception request&quot; in the HR portal at least 15 working days before the start date.</div>
</div>
<div class="ln skip">Was this article helpful? Yes / No</div>
</div>
<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk</span><span><b style="font-family:ui-monospace,monospace">[…]</b> = header the code adds</span><span><span class="skip">struck</span> = thrown away (template text, links-only section)</span><span><span class="title">italic</span> = heading, moved into the header</span></div></div>
:::

**What to notice:**

- **One article, many chunks.** The chunk _"Error 809"_ is one of 6 chunks from the VPN article, and _"4. Working from another country"_ is one of 6 from the remote work policy. A question finds the one chunk that answers it, not the whole article.
- **The tech article is cut by its parts.** Symptoms, Applies to and Steps are one chunk each, and all 6 steps stay together. The error-code table becomes one chunk per row, so "error 812" finds only its own fix.
- **The domain article is cut by its numbered rules.** Each rule keeps its exceptions with it, so rule 4's "up to 10 days" never gets separated from "longer stays need approval".
- **Not everything is kept.** The "Internal" banner and "Was this article helpful?" are template text in every article, so they're thrown away. _Related articles_ is only links, with no answer in it, so it's skipped too. The _Error codes_ heading has no text of its own, so it isn't a chunk; its rows are.


**Alternative docs: when articles don't follow a template**

Everything above assumes articles follow a template with real headings, steps and tables. Many knowledge bases also hold articles that don't: old migrated articles, one long block of text, pasted email threads, attached Word or PDF files. For those, cutting at headings doesn't work, because there are no headings to cut at. Decide per article:

| Article looks like | Best strategy | Overlap? |
|---|---|---|
| Template with headings (Symptoms / Steps / Error codes, numbered rules) | **Structure first**, as above: one chunk per heading or table row; characters only as a fallback | No: cuts land at the end of a section |
| No headings: one long block, an email thread, a migrated article | **Recursive splitter** as the main cut: paragraph → line → sentence, about 800–1,200 characters | **Yes, about 10–15%** (100–150 characters), because cuts can land mid-thought |
| Mixed: some headings, but some sections are very long | Structure first, then the recursive splitter **inside** each long section | Only between pieces of the same long section |

**Why overlap helps here:** without headings, the splitter can't tell where one idea ends. A cut might fall between "Restart the client" and "…then clear the cache". The overlap means that pair appears whole in at least one piece, so search can still find it.

**Choosing per article** (sketch):

```python
def chunk_any(article_html: str) -> list[str]:
    sections = units(article_html)                        # structure first
    if len(sections) >= 2:                                # the article has real headings
        return [piece for h, lines in sections
                for piece in recursive_split("\n".join(lines), overlap=150)]   # fallback inside long sections
    return recursive_split(plain_text(article_html), overlap=150)               # no structure: recursive + overlap
```

**Ranked alternatives for these articles:**

| Rank | Strategy | How it cuts | Best for | Pro | Con |
|---|---|---|---|---|---|
| 1st | **Recursive splitter with overlap** | Paragraph → line → sentence, about 800–1,200 characters, 10–15% overlap | Anything, as the safe default | Cheap, predictable, works on any text | Doesn't know where an idea ends, so overlap patches the cuts |
| 2nd | **Layout-aware parsing** (Unstructured `chunk_by_title`, Docling, Azure Document Intelligence, AWS Textract) | Reads the layout: bold or large text as headings, lists, tables; cuts per element or by title | Attached Word and PDF files whose headings are visual, not written as `<h2>` | Structure cuts without hand-written patterns; tables stay whole | Heavier and slower, sometimes a paid service; can misread messy files |
| 3rd | **Semantic chunking** (LangChain `SemanticChunker`, LlamaIndex semantic splitter) | Embeds every sentence and cuts where neighbors stop being similar | Long free text that changes topic: meeting notes, email threads | Chunks follow topics, not character counts | An embedding call per sentence, uneven sizes, a threshold to tune; often barely beats recursive |

**Add-ons that work on top of any of them:**

- **Contextual headers:** the `[KB number | knowledge base | category | title | section]` line above, or a one-line summary of the whole article added to each chunk (often called contextual retrieval). Helps every splitter.
- **Parent–child ("small-to-big"):** search small chunks for precision, then give the AI the larger section they came from.
- **Sentence window:** store single sentences, and return each one with its neighbors.
- **Late chunking:** embed the whole article with a long-context model first, then split, so each chunk "knows" the rest. Needs special models.

**Usually not worth it as the main method:** AI-rewritten "proposition" chunks (high quality but slow and expensive at scale), and fixed-size cuts with no overlap (useful only as a baseline to compare against).

**How to choose:**

1. Template with headings → structure first.
2. Visual headings in attached files → layout-aware parsing.
3. No structure at all → recursive splitter with overlap; try semantic chunking only if evals show recursive missing answers.
4. Always add contextual headers; add parent–child when answers need more than one chunk.
5. Decide with numbers: run the same questions through each method and compare hit@1 and MRR.

**In an interview:** "Structure first when articles follow a template. Layout-aware parsing when the format varies but headings are visual. A recursive splitter with overlap as the safe default for free text, and semantic chunking only if evals justify the cost. Every chunk gets a header saying which article and section it came from."

**Three things that are different in ServiceApps:**

- **Permissions.** KB articles have read rules (user criteria). An assistant must never show a chunk the user can't open in ServiceApps. Store who may read each article, filter search results by it, or check access through ServiceApps with the user's own login before showing an answer.
- **Lifecycle.** Articles move through draft, review, published and retired. Index only published articles, and remove chunks when an article is retired or expires (`valid_to`).
- **Change detection is the norm.** A KB can hold thousands of articles that change daily, so re-embedding everything each time isn't an option. A content hash per article (which NurseOps Now doesn't have yet; see [Honest gaps](#honest-gaps)) is required here.

**Build or buy.** ServiceApps has its own AI Search and Now Assist, which index KB articles inside the platform. The pattern above fits when the assistant lives outside ServiceApps, or must combine KB articles with other sources (SharePoint, file shares, tickets) in one search.

**Interview answers: ServiceApps**

1. _"How would you build RAG over our ServiceApps knowledge base?"_ "I'd pull published articles from `kb_knowledge` through the REST Table API, a page at a time. I'd cut each article at its own headings, not every 500 characters, so a chunk is one complete section, and put the KB number, knowledge base, category and section in a header on every chunk. Characters only come in as a size limit for very long sections. Then I'd embed the chunks, store them with their metadata, and cite the KB number and section in every answer."
2. _"How do you handle tech articles versus policy articles?"_ "The unit changes, the idea doesn't. In a how-to article I keep the numbered steps together, because half a fix is worse than none, and each error code becomes its own chunk so 'error 809' finds exactly one answer. In a policy article each numbered rule is a chunk with its exceptions kept in it, so 'up to 10 days' is never separated from 'longer needs approval'."
3. _"How do you keep the index in sync when articles change?"_ "I store a content hash per article and re-embed only the articles whose hash changed, deleting their old chunks by `sys_id` first so there are no duplicates. I index only published articles, and remove chunks when an article is retired or passes its valid-to date. That keeps a large KB current without re-embedding everything every night."
4. _"How do you stop the assistant from leaking restricted articles?"_ "Permissions go into the index. Each chunk carries the article's read rules, and search filters by what the current user is allowed to see. For high-risk content I'd also confirm access through ServiceApps with the user's own login before showing the answer. And because many people can edit articles, I flag injection-like text and mask personal data at ingestion."
5. _"Why not just use Now Assist or AI Search?"_ "If the assistant lives inside ServiceApps and only needs KB articles, the built-in AI Search is the simpler choice. I'd build this pipeline when the assistant runs outside ServiceApps, or has to search KB articles together with other sources, or when we need full control over chunking, citations and evaluation."

**In plain terms:** the same index cards, but the binder is now a company help center. Cards are cut at each article heading, every card says which article and section it came from, and the drawer only hands out the cards a reader is allowed to see.
:::

## Why we ingest this way

**The job.** NurseOps Now helps nurses review prior authorization requests: a doctor asks the health plan to pay for an MRI, and a nurse checks the request against the plan's medical policy. The AI's job is to find the exact policy rule that applies and quote it with its page number, so the nurse can check it in seconds.

**The problem.** A policy is a 5-page PDF. The AI can't usefully read every policy for every question, and a search engine can't return "page 1" as an answer. So before any question arrives, each PDF is cut into small pieces (chunks), and each piece is stored so it can be found by meaning.

**The choice: cut where the policy cuts.** Most RAG tutorials cut text every N characters, for example every 500. We tried that on the real knee policy (on Nov 19, 2026), and the first cut landed in the middle of a word:

```
...B. Acute injury with inability to bear weight or a locked knee (conservative care not
   required); X-r          <- piece 0 ends here
ay first to rule out fracture.          <- piece 1 starts here
```

Piece 0 also mixes four rules (§1, §2, §2.A and half of §2.B), and piece 1 starts with "ay first to rule out fracture" with no policy name at all. If search returns piece 1, the AI sees a rule fragment and has no idea which policy, version or page it came from.

So NurseOps Now cuts at the policy's own structure: every numbered section ("3. Required documentation") and every lettered rule ("A. Suspected meniscus..."). One chunk is one whole rule. Each chunk also starts with a label saying whose rule it is: policy number, version, CPT code, section and page.

### See it: one policy, cut two ways

Here are pages 1–2 of the real knee policy, run through the real code on Nov 19, 2026. Picture 1 shows what is thrown away. Picture 2 shows the 8 chunks NurseOps Now actually stores. Picture 3 shows the same text cut every 500 characters. Each colored box is one chunk. For the whole 5-page policy with all 29 chunks, see [Sub-step 3](#sub-step-3-find-the-clauses).

:::html
<div class="cv">
<style>
.cv{margin:16px 0;font-size:.92em}.cv h4{margin:18px 0 6px}.cv .note{color:var(--muted);font-size:.9em;margin:4px 0 10px}
.cv .doc{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--bg)}
.cv .ln{display:block;font-family:ui-monospace,Menlo,monospace;font-size:.85em;white-space:pre-wrap;line-height:1.45;margin:0}
.cv .skip{color:var(--muted);text-decoration:line-through;opacity:.75}
.cv .tag{display:inline-block;font:600 .75em/1.6 -apple-system,system-ui,sans-serif;border-radius:10px;padding:0 8px;color:#fff;margin:0 0 4px}
.cv .ck{border-left:5px solid var(--h);background:color-mix(in srgb,var(--h) 13%,transparent);border-radius:6px;padding:6px 10px;margin:8px 0}
.cv .hdr{font-family:ui-monospace,Menlo,monospace;font-size:.8em;color:var(--h);font-weight:600;white-space:pre-wrap;margin:0 0 2px}
.cv .gone{border:1px dashed var(--line);border-radius:6px;padding:4px 10px;margin:8px 0}
.cv .cut{display:inline-block;background:#e03131;color:#fff;font-weight:700;border-radius:4px;padding:0 4px;margin:0 2px;font-family:-apple-system,system-ui,sans-serif}
.cv .key{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.85em;margin:6px 0 4px}.cv .key span{white-space:nowrap}
.cv .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:4px}
</style>
<h4>1. What pypdf reads from page 1, and what the code throws away</h4>
<div class="note">Struck-through lines are page furniture (same on every page). They are dropped before any chunking.</div><div class="doc">
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 1/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Coverage criteria</div>
<div class="ln skip">Policy number: RHP-IMG-022        Version: 2.2</div>
<div class="ln skip">Effective date: 2026-12-01        Applies to: Regional Health Plan (all lines)</div>
<div class="ln skip">CPT codes: 73721 (lower extremity joint, without contrast)</div>
<div class="ln">1. Purpose</div>
<div class="ln">Defines when outpatient MRI of the knee is medically necessary for members.</div>
<div class="ln skip" style="text-decoration:none">… (rest of page 1)</div></div>
<h4>2. Cut by structure (what NurseOps Now does): pages 1–2 become 8 chunks</h4>
<div class="note">Each colored box is one chunk, exactly as stored. The bold first line is the <b>header the code adds</b>; it is not in the PDF. The rest is the rule, word for word.</div><div class="doc">
<div class="ck" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 1 · 73721-v2.2-1 · §1 · page 1 · 139 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §1 Purpose | page 1]</div><div class="ln">Defines when outpatient MRI of the knee is medically necessary for members.</div></div>
<div class="gone"><div class="ln skip" style="text-decoration:none">2. Covered when ONE of the following is documented</div><div class="note" style="margin:2px 0">↑ This heading has no text of its own, so it is <b>not</b> a chunk. Its title is copied into the header of each rule below (2.A–2.D), so every rule still says <i>covered when</i>.</div></div>
<div class="ck" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 2 · 73721-v2.2-2.A · §2.A · page 1 · 355 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.A Covered when ONE of the following is documented | page 1]</div><div class="ln">Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,
giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,
AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).</div></div>
<div class="ck" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 3 · 73721-v2.2-2.B · §2.B · page 1 · 233 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.B Covered when ONE of the following is documented | page 1]</div><div class="ln">Acute injury with inability to bear weight or a locked knee (conservative care not
required); X-ray first to rule out fracture.</div></div>
<div class="ck" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 4 · 73721-v2.2-2.C · §2.C · page 1 · 150 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.C Covered when ONE of the following is documented | page 1]</div><div class="ln">Suspected infection, tumor or osteonecrosis.</div></div>
<div class="ck" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 5 · 73721-v2.2-2.D · §2.D · page 1 · 132 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.D Covered when ONE of the following is documented | page 1]</div><div class="ln">Planning for knee surgery.</div></div>
<div class="ck" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 6 · 73721-v2.2-3 · §3 · page 2 · 233 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §3 Required documentation | page 2]</div><div class="ln">- Clinical note with mechanism of injury, symptoms and exam findings
- Knee X-ray report
- Records of conservative care (PT notes with dates and response)</div></div>
<div class="ck" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 7 · 73721-v2.2-4 · §4 · page 2 · 235 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §4 Not medically necessary | page 2]</div><div class="ln">- Knee pain without mechanical symptoms or exam findings, before conservative care
- Osteoarthritis already shown on X-ray, unless surgery is being planned</div></div>
<div class="ck" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 8 · 73721-v2.2-5 · §5 · page 2 · 230 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §5 Review | page 2]</div><div class="ln">A nurse reviewer applies these criteria. Requests that do not meet them are referred to
a medical director. Only a medical director may issue an adverse determination.</div></div>
</div>
<h4>3. Cut every 500 characters (the common way): the same text becomes 3 pieces</h4>
<div class="note">Same pages, no structure: a new piece starts every 500 characters, wherever that lands. The red ✂ marks each cut. No piece has a header, so nothing says which policy, version or page it came from.</div><div class="doc">
<div class="ck" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Piece 1 · 500 chars · no header</span><div class="ln">1. Purpose
Defines when outpatient MRI of the knee is medically necessary for members.
2. Covered when ONE of the following is documented
A. Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,
   giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,
   AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).
B. Acute injury with inability to bear weight or a locked knee (conservative care not
   required); X-r<span class=cut>✂</span></div></div>
<div class="ck" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Piece 2 · 500 chars · no header</span><div class="ln">ay first to rule out fracture.
C. Suspected infection, tumor or osteonecrosis.
D. Planning for knee surgery.
3. Required documentation
- Clinical note with mechanism of injury, symptoms and exam findings
- Knee X-ray report
- Records of conservative care (PT notes with dates and response)
4. Not medically necessary
- Knee pain without mechanical symptoms or exam findings, before conservative care
- Osteoarthritis already shown on X-ray, unless surgery is being planned
5. Review
A nurse reviewer <span class=cut>✂</span></div></div>
<div class="ck" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Piece 3 · 150 chars · no header</span><div class="ln">applies these criteria. Requests that do not meet them are referred to
a medical director. Only a medical director may issue an adverse determination.</div></div>
</div>
<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk</span><span><b style="font-family:ui-monospace,monospace">[…]</b> = header added by the code</span><span><span class="skip">struck</span> = thrown away</span><span><span class="cut">✂</span> = where a 500-character cut lands</span></div>
</div>
:::

**What to notice:**

- **Where the cuts are.** In picture 2 every cut sits on the policy's own numbering (1, 2.A, 2.B … 5). In picture 3 the cuts sit wherever character 500 and 1,000 land, and the first one splits "X-ray" into "X-r ✂ ay".
- **One rule per box vs. many.** Each chunk in picture 2 holds exactly one rule, with one § and one page. Piece 1 in picture 3 holds §1, the §2 heading, all of §2.A and half of §2.B. Piece 2 runs from the second half of §2.B to the start of §5.
- **The header.** Every chunk in picture 2 starts with a bold `[…]` line the code adds (policy, version, CPT code, §, page). The pieces in picture 3 have none, so piece 2 begins "ay first to rule out fracture" with no hint of where it came from.
- **Small rules stay small.** Chunk 5 (§2.D, 132 characters) stays its own chunk. Character cutting would always glue it to its neighbors.
- **The heading that isn't a chunk.** The §2 heading has no text of its own, so it isn't stored alone. Its title is copied into the headers of 2.A–2.D instead (the dashed box in picture 2).

**Why it matters for a nurse.** The AI must cite "§2.A, page 1" and quote the rule word for word, and a later step (output checks) matches every quote against the PDF. That only works if each chunk is a complete rule with its section and page attached.

**What we chose not to do (yet):** semantic chunking (cutting where the meaning changes) and late chunking. Policies already have clear numbered structure, so the structure is the best guide. Fixed-size cutting is kept only as a fallback for a rule too long to fit in one chunk.

**In plain terms:** cutting a binder into index cards, one rule per card, with the binder's name and the page number written at the top of every card, instead of cutting the binder every 3 inches with a paper cutter.

## Words used in this post

| Term | Plain meaning | Everyday example |
|---|---|---|
| Ingestion | Preparing documents ahead of time so they can be searched | Shelving and labeling books before the library opens |
| Chunk | One small piece of a document; here, one policy rule | One index card |
| Clause | One rule in a policy, such as §2.A | One numbered item in a contract |
| Contextual header | The label at the top of each chunk naming the policy, version, CPT code, section and page | The binder name written on each card |
| Page furniture | Text repeated on every page (headers, footers, page numbers) that isn't content | The letterhead on every page of a letter |
| Regular expression (regex) | A pattern that matches text, like "a number, a dot, a space, then words" | A search with wildcards |
| Embedding | Text turned into a list of numbers so similar meanings sit close together | Placing books on a map so related topics sit near each other |
| Vector store | A database that finds text by meaning, using embeddings | A librarian who finds books by topic, not by title |
| Chroma | The vector store NurseOps Now uses | |
| Re-index | Rebuilding the stored chunks after a document changes | Reprinting the cards when the binder is updated |
| CPT code | The billing code for a procedure, e.g. 73721 = MRI of the knee | A product SKU |

## How ingestion flows

Ingestion runs once per policy change, before any question, not on each request. It runs when the index is empty (the first search builds it) or when someone runs `python -m app.cli index-policies`. The order below is the real call order: `index_all()` → `index_policy()` → `chunk_policy()` → `load_pages()` → `_split_long()` → embed → Chroma.

| # | Sub-step | What happens | Code | Checked by |
|---|---|---|---|---|
| 1 | [Find the policy file](#sub-step-1-find-the-policy-file) | Look up each policy in the registry: CPT → PDF, number, version | `services/policy.py` `registry()`, `policy_path()` | `test_unknown_cpt_is_404` |
| 2 | [Read the pages](#sub-step-2-read-the-pages) | Extract text from each PDF page; drop page furniture | `rag/chunker.py` `load_pages()` | `test_clause_aware_chunks…` (no furniture in chunks) |
| 3 | [Find the clauses](#sub-step-3-find-the-clauses) | Walk the lines; start a new clause at each "2." or "A." | `chunker.py` `chunk_policy()` | `test_clause_aware_chunks…`, `test_page_numbers_follow_the_pdf` |
| 4 | [Add header, ID and metadata](#sub-step-4-add-header-id-and-metadata) | Prefix the contextual header; build the chunk ID and labels | `chunker.py` `chunk_policy()` | `test_metadata_on_every_chunk` |
| 5 | [Split long clauses](#sub-step-5-split-long-clauses) | Only if a clause is over 1,200 characters: split by paragraph → line → sentence, with overlap | `chunker.py` `_split_long()` | `test_recursive_fallback_splits_long_clauses` |
| 6 | [Flag injection-like text](#sub-step-6-flag-injection-like-text) | Mark chunks that look like hidden instructions and keep them out | `chunker.py` `INJECTION`, `index.py` `index_policy()` | `test_injection_like_text_is_flagged` |
| 7 | [Embed](#sub-step-7-embed) | Turn each chunk into 384 numbers (all-MiniLM-L6-v2) | `rag/index.py` `SentenceTransformerEmbedder` | offline `HashEmbedder` in tests |
| 8 | [Store in Chroma](#sub-step-8-store-in-chroma) | Delete the policy's old chunks, add the new ones | `index.py` `index_policy()`, `collection()` | `test_reindex_replaces_old_chunks_not_duplicates` |

All code paths are under `nursing-ai/backend/app/`.

## Sub-step details: one policy all the way through

The example all the way through is the real knee policy: **RHP-IMG-022 v2.2, MRI knee, CPT 73721** (`backend/policies/73721.pdf`, 5 pages, synthetic). Every output below is from running the code on Nov 19, 2026.

### Sub-step 1: Find the policy file

**What it does.** Looks up which PDF belongs to which CPT code, and its policy number and version, from one small JSON file.

**The code.** `backend/policies/index.json` is the registry. One row per policy:

```json
{
  "cpt": "73721",
  "title": "MRI knee",
  "number": "RHP-IMG-022",
  "version": "2.2",
  "effective": "2026-12-01",
  "file": "73721.pdf",
  "codes": "73721 (lower extremity joint, without contrast)"
}
```

`app/services/policy.py` reads it and resolves the file safely:

```python
def policy_path(cpt: str) -> tuple[Path, str]:
    p = get_policy(cpt)
    path = (POLICY_DIR / p["file"]).resolve()
    if POLICY_DIR.resolve() not in path.parents or not path.exists():
        raise NotFound(f"Policy file missing for CPT {cpt}")
    ...
```

**Why this way.** The version lives in the registry, not inside the PDF text, so it is easy to read and easy to change. The `parents` check stops a bad registry entry like `../../.env` from reading files outside the policies folder.

**In plain terms:** the card catalog that says which binder is on which shelf.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 2: Read the pages

**What it does.** Pulls the text out of each PDF page with pypdf and throws away the lines that repeat on every page.

**The code.** `app/rag/chunker.py`:

```python
# Page furniture repeated on every page: not policy content.
_SKIP = re.compile(r"^(REGIONAL HEALTH PLAN .*PAGE \d+/\d+|SYNTHETIC DEMO POLICY .*|Medical Policy: .*"
                   r"|Policy number: .*|Effective date: .*|CPT codes: .*)$")

def load_pages(path: Path) -> list[tuple[int, list[str]]]:
    """[(page_no, content lines)] with page headers/footers removed."""
    out = []
    for i, page in enumerate(PdfReader(str(path)).pages, start=1):
        lines = [ln.rstrip() for ln in (page.extract_text() or "").splitlines()]
        out.append((i, [ln for ln in lines if ln.strip() and not _SKIP.match(ln.strip())]))
    return out
```

**Real output.** Page 1 of the knee policy, as pypdf reads it, with what `_SKIP` drops:

```
SKIP  REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 1/5
SKIP  SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY
SKIP  SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY
SKIP  Medical Policy: MRI knee — Coverage criteria
SKIP  Policy number: RHP-IMG-022        Version: 2.2
SKIP  Effective date: 2026-12-01        Applies to: Regional Health Plan (all lines)
SKIP  CPT codes: 73721 (lower extremity joint, without contrast)
keep  1. Purpose
keep  Defines when outpatient MRI of the knee is medically necessary for members.
keep  2. Covered when ONE of the following is documented
keep  A. Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,
keep     giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,
keep     AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).
keep  B. Acute injury with inability to bear weight or a locked knee (conservative care not
keep     required); X-ray first to rule out fracture.
```

**Why this way.** Page furniture would otherwise land inside chunks. "SYNTHETIC DEMO POLICY" appears twice on every page, so it would look relevant to every search and waste space in every quote. The page number is kept as a number (`page_no`) instead, so citations can say "page 1".

**Trade-off.** pypdf reads text-based PDFs only. These policies are text PDFs. A scanned policy would need OCR, which NurseOps Now uses for incoming faxes (Step 2) but not for policies.

**In plain terms:** tearing the letterhead off every page before filing the letter.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 3: Find the clauses

**What it does.** Reads the lines in order and starts a new clause each time it sees a numbered section ("3. Required documentation") or a lettered rule ("A. Suspected …"). Every other line belongs to the current clause.

**The code.** Two regular expressions and a small loop in `chunk_policy()`:

```python
_SECTION = re.compile(r"^(\d+)\.\s+(.+)$")          # "2. Covered when ONE of the following is documented"
_CRITERION = re.compile(r"^([A-H])\.\s+(.+)$")      # "A. Low back pain ..."

for page_no, lines in load_pages(path):
    for ln in lines:
        s = ln.strip()
        m_sec, m_crit = _SECTION.match(s), _CRITERION.match(s)
        if m_sec:                                   # new section: "6. Definitions"
            section, section_title = m_sec.group(1), m_sec.group(2)
            cur = {"section": section, "section_title": section_title, "criterion": "",
                   "page": page_no, "lines": []}
            clauses.append(cur)
        elif m_crit and section:                    # new lettered rule inside it: "B. Mechanical symptoms ..."
            cur = {"section": section, "section_title": section_title, "criterion": m_crit.group(1),
                   "page": page_no, "lines": [m_crit.group(2)]}
            clauses.append(cur)
        elif cur is not None:                       # a wrapped line: belongs to the current clause
            cur["lines"].append(s)
# A section heading followed only by lettered criteria carries no body of its own.
clauses = [c for c in clauses if c["lines"]]
```

**Real output.** The knee policy becomes 29 clauses. Sections with lettered rules (§2, §6, §7, §8, §11) become one chunk per letter; the rest become one chunk per section:

| Chunk ID | Label | Section | Page | Characters |
|---|---|---|---|---|
| `73721-v2.2-1` | §1 | Purpose | 1 | 139 |
| `73721-v2.2-2.A` | §2.A | Covered when ONE of the following is documented | 1 | 355 |
| `73721-v2.2-2.B` | §2.B | Covered when ONE of the following is documented | 1 | 233 |
| `73721-v2.2-2.C` | §2.C | Covered when … | 1 | 150 |
| `73721-v2.2-2.D` | §2.D | Covered when … | 1 | 132 |
| `73721-v2.2-3` | §3 | Required documentation | 2 | 233 |
| `73721-v2.2-4` | §4 | Not medically necessary | 2 | 235 |
| `73721-v2.2-5` | §5 | Review | 2 | 230 |
| `73721-v2.2-6.A` … `6.D` | §6.A–D | Definitions | 3 | 155–232 |
| `73721-v2.2-7.A`, `7.B` | §7.A–B | Repeat knee MRI | 3 | 163–165 |
| `73721-v2.2-8.A` … `8.C` | §8.A–C | Post-operative imaging | 3 | 143–217 |
| `73721-v2.2-9` … `10` | §9, §10 | Prior imaging, Contrast | 4 | 215–308 |
| `73721-v2.2-11.A` … `11.C` | §11.A–C | Special populations | 4 | 160–224 |
| `73721-v2.2-12` | §12 | Osteoarthritis | 4 | 241 |
| `73721-v2.2-13` … `18` | §13–§18 | Expedited review, timelines, appeals, site of service, coding notes, history | 5 | 216–326 |

Across all three policies: **83 chunks** (lumbar spine 28, knee 29, brain 26).

**See the whole PDF and all 29 chunks.** Below is the entire knee policy, all 5 pages, exactly as the PDF reader gives it to the code (Nov 19, 2026). Every colored box is one chunk: the lines inside it are the lines from the PDF that became that chunk, and the bold `[…]` line on top is the header the code adds. Struck-through lines are thrown away. Dashed boxes are headings with no text of their own: they aren't chunks, and their title goes into the header of each rule under them. Click a label in the strip at the top to jump to that chunk.

:::html
<div class="cv">
<style>
.cv{margin:16px 0;font-size:.92em}.cv h4{margin:18px 0 6px}.cv .note{color:var(--muted);font-size:.9em;margin:4px 0 10px}
.cv .doc{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--bg)}
.cv .ln{display:block;font-family:ui-monospace,Menlo,monospace;font-size:.85em;white-space:pre-wrap;line-height:1.45;margin:0}
.cv .skip{color:var(--muted);text-decoration:line-through;opacity:.75}
.cv .tag{display:inline-block;font:600 .75em/1.6 -apple-system,system-ui,sans-serif;border-radius:10px;padding:0 8px;color:#fff;margin:0 0 4px}
.cv .ck{border-left:5px solid var(--h);background:color-mix(in srgb,var(--h) 13%,transparent);border-radius:6px;padding:6px 10px;margin:8px 0}
.cv .hdr{font-family:ui-monospace,Menlo,monospace;font-size:.8em;color:var(--h);font-weight:600;white-space:pre-wrap;margin:0 0 2px}
.cv .gone{border:1px dashed var(--line);border-radius:6px;padding:4px 10px;margin:8px 0}
.cv .cut{display:inline-block;background:#e03131;color:#fff;font-weight:700;border-radius:4px;padding:0 4px;margin:0 2px;font-family:-apple-system,system-ui,sans-serif}
.cv .page{border:1px solid var(--line);border-radius:8px;padding:8px 12px 4px;margin:12px 0;background:var(--bg)}.cv .pno{font:600 .8em/1.4 -apple-system,system-ui,sans-serif;color:var(--muted);margin:0 0 6px}.cv .strip{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 4px}.cv .strip a{color:#fff;text-decoration:none;font:600 .72em/1.7 -apple-system,system-ui,sans-serif;border-radius:9px;padding:0 7px}.cv .title{opacity:.7;font-style:italic}.cv .key{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.85em;margin:6px 0 4px}.cv .key span{white-space:nowrap}
.cv .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:4px}
</style>
<div class="note"><b>RHP-IMG-022 v2.2, MRI knee</b>: 5 pages → <b>29 chunks</b>. Click a chunk to jump to it.</div><div class="strip">
<span class="note" style="margin:0 2px 0 6px">p1</span>
<a href="#ck-73721-v2.2-1" style="background:#2b7de9">§1</a>
<a href="#ck-73721-v2.2-2.A" style="background:#e8590c">§2.A</a>
<a href="#ck-73721-v2.2-2.B" style="background:#2f9e44">§2.B</a>
<a href="#ck-73721-v2.2-2.C" style="background:#ae3ec9">§2.C</a>
<a href="#ck-73721-v2.2-2.D" style="background:#d6336c">§2.D</a>
<span class="note" style="margin:0 2px 0 6px">p2</span>
<a href="#ck-73721-v2.2-3" style="background:#1098ad">§3</a>
<a href="#ck-73721-v2.2-4" style="background:#f59f00">§4</a>
<a href="#ck-73721-v2.2-5" style="background:#5c7cfa">§5</a>
<span class="note" style="margin:0 2px 0 6px">p3</span>
<a href="#ck-73721-v2.2-6.A" style="background:#2b7de9">§6.A</a>
<a href="#ck-73721-v2.2-6.B" style="background:#e8590c">§6.B</a>
<a href="#ck-73721-v2.2-6.C" style="background:#2f9e44">§6.C</a>
<a href="#ck-73721-v2.2-6.D" style="background:#ae3ec9">§6.D</a>
<a href="#ck-73721-v2.2-7.A" style="background:#d6336c">§7.A</a>
<a href="#ck-73721-v2.2-7.B" style="background:#1098ad">§7.B</a>
<a href="#ck-73721-v2.2-8.A" style="background:#f59f00">§8.A</a>
<a href="#ck-73721-v2.2-8.B" style="background:#5c7cfa">§8.B</a>
<a href="#ck-73721-v2.2-8.C" style="background:#2b7de9">§8.C</a>
<span class="note" style="margin:0 2px 0 6px">p4</span>
<a href="#ck-73721-v2.2-9" style="background:#e8590c">§9</a>
<a href="#ck-73721-v2.2-10" style="background:#2f9e44">§10</a>
<a href="#ck-73721-v2.2-11.A" style="background:#ae3ec9">§11.A</a>
<a href="#ck-73721-v2.2-11.B" style="background:#d6336c">§11.B</a>
<a href="#ck-73721-v2.2-11.C" style="background:#1098ad">§11.C</a>
<a href="#ck-73721-v2.2-12" style="background:#f59f00">§12</a>
<span class="note" style="margin:0 2px 0 6px">p5</span>
<a href="#ck-73721-v2.2-13" style="background:#5c7cfa">§13</a>
<a href="#ck-73721-v2.2-14" style="background:#2b7de9">§14</a>
<a href="#ck-73721-v2.2-15" style="background:#e8590c">§15</a>
<a href="#ck-73721-v2.2-16" style="background:#2f9e44">§16</a>
<a href="#ck-73721-v2.2-17" style="background:#ae3ec9">§17</a>
<a href="#ck-73721-v2.2-18" style="background:#d6336c">§18</a>
</div>
<div class="page"><div class="pno">PAGE 1 OF 5</div>
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 1/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Coverage criteria</div>
<div class="ln skip">Policy number: RHP-IMG-022        Version: 2.2</div>
<div class="ln skip">Effective date: 2026-12-01        Applies to: Regional Health Plan (all lines)</div>
<div class="ln skip">CPT codes: 73721 (lower extremity joint, without contrast)</div>
<div class="ck" id="ck-73721-v2.2-1" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 1 of 29 · §1 · 139 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §1 Purpose | page 1]</div>
<div class="ln title">1. Purpose   ← title, goes into the header</div>
<div class="ln">Defines when outpatient MRI of the knee is medically necessary for members.</div>
</div>
<div class="gone"><div class="ln">2. Covered when ONE of the following is documented</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>
<div class="ck" id="ck-73721-v2.2-2.A" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 2 of 29 · §2.A · 355 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.A Covered when ONE of the following is documented | page 1]</div>
<div class="ln">A. Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,</div>
<div class="ln">   giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,</div>
<div class="ln">   AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).</div>
</div>
<div class="ck" id="ck-73721-v2.2-2.B" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 3 of 29 · §2.B · 233 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.B Covered when ONE of the following is documented | page 1]</div>
<div class="ln">B. Acute injury with inability to bear weight or a locked knee (conservative care not</div>
<div class="ln">   required); X-ray first to rule out fracture.</div>
</div>
<div class="ck" id="ck-73721-v2.2-2.C" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 4 of 29 · §2.C · 150 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.C Covered when ONE of the following is documented | page 1]</div>
<div class="ln">C. Suspected infection, tumor or osteonecrosis.</div>
</div>
<div class="ck" id="ck-73721-v2.2-2.D" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 5 of 29 · §2.D · 132 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.D Covered when ONE of the following is documented | page 1]</div>
<div class="ln">D. Planning for knee surgery.</div>
</div>
</div>
<div class="page"><div class="pno">PAGE 2 OF 5</div>
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 2/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Documentation and exclusions</div>
<div class="ck" id="ck-73721-v2.2-3" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 6 of 29 · §3 · 233 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §3 Required documentation | page 2]</div>
<div class="ln title">3. Required documentation   ← title, goes into the header</div>
<div class="ln">- Clinical note with mechanism of injury, symptoms and exam findings</div>
<div class="ln">- Knee X-ray report</div>
<div class="ln">- Records of conservative care (PT notes with dates and response)</div>
</div>
<div class="ck" id="ck-73721-v2.2-4" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 7 of 29 · §4 · 235 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §4 Not medically necessary | page 2]</div>
<div class="ln title">4. Not medically necessary   ← title, goes into the header</div>
<div class="ln">- Knee pain without mechanical symptoms or exam findings, before conservative care</div>
<div class="ln">- Osteoarthritis already shown on X-ray, unless surgery is being planned</div>
</div>
<div class="ck" id="ck-73721-v2.2-5" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 8 of 29 · §5 · 230 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §5 Review | page 2]</div>
<div class="ln title">5. Review   ← title, goes into the header</div>
<div class="ln">A nurse reviewer applies these criteria. Requests that do not meet them are referred to</div>
<div class="ln">a medical director. Only a medical director may issue an adverse determination.</div>
</div>
</div>
<div class="page"><div class="pno">PAGE 3 OF 5</div>
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 3/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Definitions and repeat imaging</div>
<div class="gone"><div class="ln">6. Definitions</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>
<div class="ck" id="ck-73721-v2.2-6.A" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 9 of 29 · §6.A · 232 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §6.A Definitions | page 3]</div>
<div class="ln">A. Conservative care: physical therapy or a supervised home exercise plan, activity</div>
<div class="ln">   change, bracing and/or NSAIDs for at least 4 to 6 weeks, with dates and response.</div>
</div>
<div class="ck" id="ck-73721-v2.2-6.B" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 10 of 29 · §6.B · 155 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §6.B Definitions | page 3]</div>
<div class="ln">B. Mechanical symptoms: locking, catching or the knee giving way during normal</div>
<div class="ln">   activity.</div>
</div>
<div class="ck" id="ck-73721-v2.2-6.C" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 11 of 29 · §6.C · 209 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §6.C Definitions | page 3]</div>
<div class="ln">C. Positive exam test: a McMurray, Lachman, anterior or posterior drawer, or pivot</div>
<div class="ln">   shift test recorded as positive by the examining clinician.</div>
</div>
<div class="ck" id="ck-73721-v2.2-6.D" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 12 of 29 · §6.D · 173 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §6.D Definitions | page 3]</div>
<div class="ln">D. Unable to bear weight: the member cannot take four steps, both right after the</div>
<div class="ln">   injury and at the visit.</div>
</div>
<div class="gone"><div class="ln">7. Repeat knee MRI</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>
<div class="ck" id="ck-73721-v2.2-7.A" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 13 of 29 · §7.A · 165 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §7.A Repeat knee MRI | page 3]</div>
<div class="ln">A. Covered when a new injury or clearly new mechanical symptoms appear after a prior</div>
<div class="ln">   knee MRI.</div>
</div>
<div class="ck" id="ck-73721-v2.2-7.B" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 14 of 29 · §7.B · 163 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §7.B Repeat knee MRI | page 3]</div>
<div class="ln">B. Not covered within 12 months of a prior MRI of the same knee when symptoms are</div>
<div class="ln">   unchanged.</div>
</div>
<div class="gone"><div class="ln">8. Post-operative imaging</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>
<div class="ck" id="ck-73721-v2.2-8.A" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 15 of 29 · §8.A · 217 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §8.A Post-operative imaging | page 3]</div>
<div class="ln">A. Covered after meniscus repair or ligament reconstruction for a suspected re-tear,</div>
<div class="ln">   with new mechanical symptoms and a positive exam test.</div>
</div>
<div class="ck" id="ck-73721-v2.2-8.B" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 16 of 29 · §8.B · 144 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §8.B Post-operative imaging | page 3]</div>
<div class="ln">B. Covered at any time for suspected infection after knee surgery.</div>
</div>
<div class="ck" id="ck-73721-v2.2-8.C" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 17 of 29 · §8.C · 143 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §8.C Post-operative imaging | page 3]</div>
<div class="ln">C. Routine imaging after surgery to check healing is not covered.</div>
</div>
</div>
<div class="page"><div class="pno">PAGE 4 OF 5</div>
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 4/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Prior imaging, contrast and special populations</div>
<div class="ck" id="ck-73721-v2.2-9" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 18 of 29 · §9 · 308 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §9 Prior imaging | page 4]</div>
<div class="ln title">9. Prior imaging   ← title, goes into the header</div>
<div class="ln">- A weight-bearing knee X-ray from the last 6 months is required before MRI.</div>
<div class="ln">- After an acute injury, X-ray comes first to rule out a fracture (Ottawa knee rules).</div>
<div class="ln">- X-ray is not needed first for a suspected infection or tumor in a child.</div>
</div>
<div class="ck" id="ck-73721-v2.2-10" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 19 of 29 · §10 · 215 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §10 Contrast | page 4]</div>
<div class="ln title">10. Contrast   ← title, goes into the header</div>
<div class="ln">MR arthrography (joint contrast) and MRI with IV contrast are reviewed under a</div>
<div class="ln">separate policy. Contrast is mainly used after prior meniscus surgery.</div>
</div>
<div class="gone"><div class="ln">11. Special populations</div><div class="note" style="margin:2px 0">↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>
<div class="ck" id="ck-73721-v2.2-11.A" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 20 of 29 · §11.A · 224 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §11.A Special populations | page 4]</div>
<div class="ln">A. Members under 18: covered for suspected osteochondritis dissecans, a locked knee</div>
<div class="ln">   or a suspected tumor. Growth plate injuries need an X-ray first.</div>
</div>
<div class="ck" id="ck-73721-v2.2-11.B" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 21 of 29 · §11.B · 162 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §11.B Special populations | page 4]</div>
<div class="ln">B. Athletes: return-to-play timing alone does not make a knee MRI medically</div>
<div class="ln">   necessary.</div>
</div>
<div class="ck" id="ck-73721-v2.2-11.C" style="--h:#1098ad"><span class="tag" style="background:#1098ad">Chunk 22 of 29 · §11.C · 160 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §11.C Special populations | page 4]</div>
<div class="ln">C. Implanted devices: knee replacement hardware limits MRI; CT is usually preferred.</div>
</div>
<div class="ck" id="ck-73721-v2.2-12" style="--h:#f59f00"><span class="tag" style="background:#f59f00">Chunk 23 of 29 · §12 · 241 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §12 Osteoarthritis | page 4]</div>
<div class="ln title">12. Osteoarthritis   ← title, goes into the header</div>
<div class="ln">MRI is not medically necessary to diagnose or stage osteoarthritis; X-ray is the test</div>
<div class="ln">of choice. MRI may be covered when surgery other than joint replacement is planned.</div>
</div>
</div>
<div class="page"><div class="pno">PAGE 5 OF 5</div>
<div class="ln skip">REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT   PAGE 5/5</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY</div>
<div class="ln skip">Medical Policy: MRI knee — Review process and administration</div>
<div class="ck" id="ck-73721-v2.2-13" style="--h:#5c7cfa"><span class="tag" style="background:#5c7cfa">Chunk 24 of 29 · §13 · 282 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §13 Expedited review | page 5]</div>
<div class="ln title">13. Expedited review   ← title, goes into the header</div>
<div class="ln">A request is reviewed within 72 hours when the provider states that waiting could</div>
<div class="ln">seriously harm the member&#x27;s life, health or ability to regain function, for example</div>
<div class="ln">a locked knee that cannot be straightened.</div>
</div>
<div class="ck" id="ck-73721-v2.2-14" style="--h:#2b7de9"><span class="tag" style="background:#2b7de9">Chunk 25 of 29 · §14 · 236 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §14 Standard review timelines | page 5]</div>
<div class="ln title">14. Standard review timelines   ← title, goes into the header</div>
<div class="ln">A decision is made within 7 calendar days of a complete request. Missing documents</div>
<div class="ln">pause the clock; the provider is asked for them within 1 business day.</div>
</div>
<div class="ck" id="ck-73721-v2.2-15" style="--h:#e8590c"><span class="tag" style="background:#e8590c">Chunk 26 of 29 · §15 · 326 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §15 Peer-to-peer and appeals | page 5]</div>
<div class="ln title">15. Peer-to-peer and appeals   ← title, goes into the header</div>
<div class="ln">The ordering provider may ask for a peer-to-peer discussion with the medical director</div>
<div class="ln">within 14 days of an adverse determination. A written appeal may be filed within</div>
<div class="ln">180 days and is decided by a reviewer who was not part of the first decision.</div>
</div>
<div class="ck" id="ck-73721-v2.2-16" style="--h:#2f9e44"><span class="tag" style="background:#2f9e44">Chunk 27 of 29 · §16 · 244 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §16 Site of service | page 5]</div>
<div class="ln title">16. Site of service   ← title, goes into the header</div>
<div class="ln">Outpatient MRI should be done at a freestanding imaging center when one is available</div>
<div class="ln">within 30 miles. Hospital outpatient imaging is covered when no such center is nearby.</div>
</div>
<div class="ck" id="ck-73721-v2.2-17" style="--h:#ae3ec9"><span class="tag" style="background:#ae3ec9">Chunk 28 of 29 · §17 · 216 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §17 Coding notes | page 5]</div>
<div class="ln title">17. Coding notes   ← title, goes into the header</div>
<div class="ln">One knee per request; MRI of both knees needs two requests. Ankle and hip MRI</div>
<div class="ln">under the same CPT code are reviewed under the joint imaging policy.</div>
</div>
<div class="ck" id="ck-73721-v2.2-18" style="--h:#d6336c"><span class="tag" style="background:#d6336c">Chunk 29 of 29 · §18 · 258 chars</span><div class="hdr">[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §18 Policy history | page 5]</div>
<div class="ln title">18. Policy history   ← title, goes into the header</div>
<div class="ln">Version 2.2 (2026-12-01): added definitions, repeat and post-operative imaging,</div>
<div class="ln">special populations and review timelines. Version 2.1 (2026-04-01): conservative</div>
<div class="ln">care set at 4 to 6 weeks.</div>
</div>
</div>
<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk (its lines from the PDF)</span><span><b style="font-family:ui-monospace,monospace">[…]</b> = header the code adds</span><span><span class="skip">struck</span> = thrown away</span><span><span class="title">italic</span> = section title, moved into the header</span></div></div>
:::

**What to notice in the whole document:**

- **Every page starts clean.** Each page starts with 4 header lines (plan name, two "synthetic" banners, and the policy title with that page's topic), and the code throws them all away: 23 lines in total, counting the 3 extra policy-detail lines on page 1.
- **29 chunks, 5 headings.** §2, §6, §7, §8 and §11 have lettered rules under them, so the headings aren't chunks; each letter is. The other 13 sections have no letters, so each whole section is one chunk.
- **No chunk crosses a page.** Each page starts with a new section, so every chunk has exactly one page number to cite.
- **Sizes vary, on purpose.** The smallest chunk is 132 characters (§2.D) and the largest is 355 (§2.A). The cut follows the rule, not a target size.

**Why this way.** The policy's own numbering is the most reliable boundary there is: the author already decided where one rule ends. The `§2` heading itself ("Covered when ONE of the following is documented") has no body, so it is dropped as a chunk, but its title is kept on every §2 rule. That way §2.A still says _covered when_ even when read alone.

**Trade-off.** It depends on the PDF using "2." and "A." at the start of a line. A policy written as "Section 2(a)" would need a new pattern. The tests pin the current format, so a change would be caught.

**In plain terms:** reading a contract and starting a new card every time you see a new item number.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 4: Add header, ID and metadata

**What it does.** Writes a one-line label at the top of every chunk, gives it a stable ID, and stores labels (metadata) next to it for filtering and citing.

**The code.**

```python
label = f"§{c['section']}" + (f".{c['criterion']}" if c["criterion"] else "")
header = (f"[{policy['number']} v{policy['version']} | {policy['title']} | CPT {policy['cpt']} | "
          f"{label} {c['section_title']} | page {c['page']}]")
body = "\n".join(c["lines"])
for n, piece in enumerate(_split_long(body)):
    cid = f"{policy['cpt']}-v{policy['version']}-{label.lstrip('§')}" + (f"-{n}" if n else "")
    chunks.append(Chunk(id=cid, text=f"{header}\n{piece}", meta={
        "cpt": policy["cpt"], "policy_number": policy["number"], "version": policy["version"],
        "title": policy["title"], "section": c["section"], "section_title": c["section_title"],
        "criterion": c["criterion"], "label": label, "page": c["page"],
        "flagged": bool(INJECTION.search(piece)),
    }))
```

**Real output.** Chunk `73721-v2.2-2.A`, exactly as stored:

```
[RHP-IMG-022 v2.2 | MRI knee | CPT 73721 | §2.A Covered when ONE of the following is documented | page 1]
Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,
giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,
AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).
```

and its metadata:

```python
{'cpt': '73721', 'policy_number': 'RHP-IMG-022', 'version': '2.2', 'title': 'MRI knee',
 'section': '2', 'section_title': 'Covered when ONE of the following is documented',
 'criterion': 'A', 'label': '§2.A', 'page': 1, 'flagged': False}
```

**Why this way.** The header and the metadata do different jobs:

- **The header is part of the text**, so it is embedded too. A search for "knee MRI coverage" is pulled toward knee chunks even when the rule body never says "knee". A nurse or Claude reading the chunk alone knows whose rule it is.
- **The metadata is for code.** Search filters on `cpt` so a knee question never returns a spine rule. The review cites `label` and `page`. The audit trail stores `version`.
- **The quote leaves the header out.** `body_of()` strips the header, so the quote that output checks match against the PDF is the policy's real wording:

```python
def body_of(chunk_text: str) -> str:
    """Chunk text without its contextual header (the quotable policy wording)."""
    return chunk_text.split("\n", 1)[1] if chunk_text.startswith("[") and "\n" in chunk_text else chunk_text
```

**Why the ID looks like that.** `73721-v2.2-2.A` is readable in logs and traces, and is the same every time the policy is indexed. The `-1`, `-2` suffix appears only when a long clause is split (sub-step 5).

**In plain terms:** writing the binder name, edition and page on top of each card, and also filing the card under the right tab so it can be pulled out quickly.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 5: Split long clauses

**What it does.** If one clause is longer than 1,200 characters, it is split again: first at blank lines, then at line breaks, then at sentence ends, with 150 characters repeated between pieces. Only as a last resort is it cut every 1,050 characters.

**The code.**

```python
MAX_CHARS = 1200      # recursive fallback above this
OVERLAP = 150

def _split_long(text: str) -> list[str]:
    """Recursive fallback: paragraphs -> lines -> hard cut, with overlap."""
    if len(text) <= MAX_CHARS:
        return [text]
    for sep in ("\n\n", "\n", ". "):
        parts = text.split(sep)
        if len(parts) > 1:
            out, cur = [], ""
            for p in parts:
                cand = f"{cur}{sep}{p}" if cur else p
                if len(cand) > MAX_CHARS and cur:
                    out.append(cur)
                    cur = cur[-OVERLAP:] + sep + p      # carry the last 150 chars forward
                else:
                    cur = cand
            out.append(cur)
            return [s for piece in out for s in _split_long(piece)] if any(len(o) > MAX_CHARS for o in out) else out
    return [text[i:i + MAX_CHARS] for i in range(0, len(text), MAX_CHARS - OVERLAP)]
```

**Real output.** On today's three policies this fallback **never fires**. The longest chunk is 487 characters (lumbar spine) and the knee's longest is 355. It is there for a future policy with a long rule. The unit test feeds it a 3,600-character clause and checks every piece is 1,200 characters or less.

**Why this way.** It keeps the clause rule as the main rule and only falls back to size when it must. The overlap means a sentence that straddles a cut still appears whole in at least one piece.

**Why 1,200.** all-MiniLM-L6-v2 reads at most 256 word-pieces (about 1,000–1,200 characters of English) and silently ignores the rest. A chunk longer than that would be only partly embedded, so its end could never be found by meaning.

**In plain terms:** if one rule doesn't fit on a card, continue it on a second card and repeat the last line at the top so nothing is lost between them.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 6: Flag injection-like text

**What it does.** Checks every chunk for text that looks like an instruction to the AI ("ignore previous instructions", "SYSTEM:"), and keeps any such chunk out of the index.

**The code.**

```python
# Injection-like text inside a document must never reach the index unflagged.
INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above) instructions|^\s*system\s*:"
                       r"|you are now|disregard (the|your) (rules|instructions)", re.I | re.M)
```

and in `index_policy()`:

```python
flagged = [c.id for c in chunks if c.meta["flagged"]]
keep = [c for c in chunks if not c.meta["flagged"]]
```

**Real output.** 0 of 83 chunks are flagged today. The CLI prints flagged IDs as `FLAGGED (kept out)` when there are any.

**Why this way.** Anything in the index can end up in Claude's prompt as "policy text". A poisoned policy file is a prompt injection that arrives through search, which is harder to spot than one typed into the chat. Blocking it here is cheap. The input guardrails (Step 3) and the fax scan (Step 2) cover the other ways in.

**Trade-off.** A pattern list only catches known phrasings. It is one layer; the system prompt and the output checks are others.

**In plain terms:** a mailroom that pulls any letter saying "ignore your boss and do what this letter says".

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 7: Embed

**What it does.** Turns each chunk's text, header included, into a list of 384 numbers that capture its meaning, using the small open model all-MiniLM-L6-v2 on the server. Claude is never used for embedding.

**The code.** `app/rag/index.py`:

```python
class SentenceTransformerEmbedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer  # heavy import: only when used
        self.name = model
        self._m = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._m.encode(texts, normalize_embeddings=True).tolist()
```

The model comes from settings (`EMBED_MODEL`, default `sentence-transformers/all-MiniLM-L6-v2`).

**Real output** (Nov 19, 2026, on a Mac, model already downloaded; 4.4 s including loading the model):

```
dims 384   first 5 numbers of "my knee keeps giving out": [-0.068, 0.064, 0.009, -0.038, 0.001]
similarity("my knee keeps giving out", §2.A meniscus/ligament rule) = 0.493
similarity("my knee keeps giving out", §17 Coding notes)             = 0.418
```

The right rule scores higher, but only by 0.075. That narrow gap is why the later steps exist: keyword search, query rewriting and re-ranking (Steps 4–6) push the right rule clearly to the top.

**Why this way.**

- **Local and free:** no API cost per chunk, no policy text sent out to embed, and it runs offline.
- **Normalized vectors** (`normalize_embeddings=True`), so cosine similarity is a plain dot product and Chroma's cosine distance matches it.
- **Small and fast:** 384 numbers per chunk, 83 chunks in total. A larger model would cost more memory on the Fly.io machine for little gain at this size. Part C of the eval plan is where a model comparison would go.
- **Tests never download it.** They swap in `HashEmbedder`, a tiny word-counting embedder, through `set_embedder()`, so the 11 RAG tests run offline in about a second.

**In plain terms:** giving every card a map coordinate so cards about the same thing sit close together.

[↑ Back to the flow](#how-ingestion-flows)

### Sub-step 8: Store in Chroma

**What it does.** Saves the chunks, their numbers and their labels in Chroma on disk, replacing whatever was stored for that policy before.

**The code.**

```python
def collection():
    ...
    _client = chromadb.PersistentClient(path=str(settings.chroma_dir))   # backend/data/chroma
    # Embeddings are always passed in, so Chroma's own default model is never used.
    return _client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"},
                                            embedding_function=None)

def index_policy(p: dict) -> dict:
    path, _ = policy_svc.policy_path(p["cpt"])
    chunks = chunk_policy(path, p)
    flagged = [c.id for c in chunks if c.meta["flagged"]]
    keep = [c for c in chunks if not c.meta["flagged"]]
    col = collection()
    col.delete(where={"cpt": p["cpt"]})          # old version(s) of this policy out
    if keep:
        col.add(ids=[c.id for c in keep], documents=[c.text for c in keep],
                metadatas=[c.meta for c in keep], embeddings=embedder().embed([c.text for c in keep]))
    return {"cpt": p["cpt"], "version": p["version"], "chunks": len(keep), "flagged": flagged}
```

**Real output.** `python -m app.cli index-policies` prints:

```
Embedder: sentence-transformers/all-MiniLM-L6-v2
  CPT 72148 v3.3: 28 chunks
  CPT 73721 v2.2: 29 chunks
  CPT 70551 v4.1: 26 chunks
Total chunks: 83
```

**Why this way.**

- **Delete, then add, per CPT code.** Re-indexing twice gives the same 83 chunks, never 166 duplicates (tested). When a policy moves from v2.2 to v2.3, all v2.2 chunks go and only v2.3 remains, so search can't mix two versions of the same rule.
- **`embedding_function=None`.** Chroma would otherwise quietly embed with its own default model. Passing embeddings in makes sure the same model embeds the chunks and the questions.
- **Cosine space**, to match the normalized vectors from sub-step 7.
- **One collection, filtered by CPT.** Every search passes `where={"cpt": ...}`, so it only looks at the one policy for the procedure on the request (8 to 29 chunks), not all 83.

The AI Assist user guide (`backend/knowledge/guide_me.pdf`) goes through the same steps into a second collection, `guide`, with one chunk per numbered section (`guide_chunks()`, `index_guide()`).

**In plain terms:** filing the new cards and throwing out the old edition's cards in the same move, so the drawer never holds two versions of a rule.

[↑ Back to the flow](#how-ingestion-flows)


## Try it yourself

From `nursing-ai/backend` with the virtual environment active:

```bash
# Rebuild the index and see the chunk counts
python -m app.cli index-policies

# See every chunk of the knee policy with its label and page
python -c "from app.rag import index; [print(c.id, c.meta['label'], c.meta['page']) for c in index.chunks_for('73721')]"

# Run the ingestion and search tests (offline, about 1 second)
python -m pytest tests/test_rag.py -q
```

## How it's tested

`backend/tests/test_rag.py`. All 11 tests passed on Nov 19, 2026 in 1.01 s, using the offline `HashEmbedder`.

| Test | What it proves |
|---|---|
| `test_clause_aware_chunks_one_per_criterion_with_header` | Each lettered rule is its own chunk, starts with the right header, keeps its full wording, and no page furniture gets in |
| `test_metadata_on_every_chunk` | Every chunk of all 3 policies has its CPT, version, policy number and a page from 1 to 5 |
| `test_page_numbers_follow_the_pdf` | §2.A is on page 1 and §3 on page 2, as in the PDF |
| `test_recursive_fallback_splits_long_clauses` | A 3,600-character clause is split into pieces of 1,200 or less |
| `test_injection_like_text_is_flagged` | "IGNORE previous instructions" and "SYSTEM:" are caught; a normal policy sentence is not |
| `test_reindex_replaces_old_chunks_not_duplicates` | Indexing twice gives the same count, with no duplicates |
| `test_search_builds_index_on_first_use` | An empty index is built automatically on the first search |
| `test_search_is_filtered_to_the_cpt_policy` | A knee search only returns knee chunks |
| `test_exact_clause_ranks_first` | "saddle numbness bowel bladder cauda equina" returns §2.B of the spine policy first |

The last three cover search (Steps 5–6) as much as ingestion, but they only pass if ingestion stored the right chunks.

## Checklist: what is done and what is next

| Item | Status | Result |
|---|---|---|
| [Clause-aware chunks with headers](#sub-step-3-find-the-clauses) | ✅ Done | 83 chunks, one rule each |
| [Metadata for filter, cite and audit](#sub-step-4-add-header-id-and-metadata) | ✅ Done | CPT, version, label, page on every chunk |
| [Long-clause fallback](#sub-step-5-split-long-clauses) | ✅ Built, not used yet | Longest chunk today: 487 characters |
| [Injection flag at ingestion](#sub-step-6-flag-injection-like-text) | ✅ Done | 0 of 83 flagged |
| [Re-index without duplicates](#sub-step-8-store-in-chroma) | ✅ Done | Tested |
| Measure clause vs fixed-size chunks on the same questions | ⬜ To do | Eval plan [Part C](../nurseops-now-evals.html#c-ablation-what-each-layer-adds) |
| Re-index only changed policies (content hash) | ⬜ Not built | See [Honest gaps](#honest-gaps) |

## Honest gaps

- **The clause choice isn't measured yet.** The fixed-size example above shows a rule cut in half, but there is no score yet saying how much clause chunks improve search. Part C of the eval plan runs the same questions with fixed-size chunks and with clause chunks and reports hit@1 and MRR for both.
- **There is no content hash today.** The feature blog says "a content hash re-indexes only the files that changed". The code doesn't do that: `index-policies` re-reads and re-embeds every policy (83 chunks, a few seconds), and a search rebuilds the index only when it is empty. Each policy is replaced as a whole, so there are no stale duplicates, but nothing detects which file changed. Either the code needs a hash per file, or the feature blog needs correcting.
- **Only the newest version is searchable.** Re-indexing deletes every older version of a policy. Reviews store the chunks and version they used, so past decisions stay auditable, but a case can't be re-run against last year's version.
- **One known retrieval miss starts here.** In Step 0, "What documents are required for a knee MRI?" returned §17 _Coding notes_ instead of §3 _Required documentation_. Both chunks are short and both mention requests and documents. Whether the fix belongs in ingestion (for example, adding the section title to the keyword index more strongly) or in search is a question for Part C.

## Interview answer

"Our policies are 5-page PDFs, so before any question we cut them into chunks. Instead of cutting every 500 characters, which in our knee policy split a rule mid-word, we cut at the policy's own clauses, so one chunk is one complete rule. Each chunk carries a header with the policy, version, CPT code, section and page, so it makes sense alone and can be cited. That metadata also lets search filter to the one policy for the procedure. Long clauses fall back to a recursive split with overlap, injection-like text is kept out of the index, and we embed locally with all-MiniLM-L6-v2 into Chroma, replacing a policy's old chunks on re-index. The next step is measuring clause versus fixed-size chunks on the same questions."

## What this proves

Ingestion in NurseOps Now is a deliberate design, not a library default. Every chunk is a whole policy rule with its source attached, which makes citation, quote checking and policy filtering possible in the later steps. It is unit tested, and the parts that aren't proven or aren't built yet (the clause-vs-fixed score and the content hash) are named, with the plan step that closes each one.

All policies and cases are synthetic. No real patient data is used.

[← Back to Step 1 in the eval plan](../nurseops-now-evals.html#step-1-ingestion)
