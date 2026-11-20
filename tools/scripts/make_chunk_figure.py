"""Build the 'See it: one policy, cut two ways' figure for docs/blog/deep-dives/01-ingestion.md from the REAL chunker output
(knee policy 73721, pages 1-2). Lines use <div>, not <p>, so blog glossary terms are not linked inside the figure.

Usage (from backend/, venv active):  PYTHONPATH=. python ../tools/scripts/make_chunk_figure.py [--full] > /tmp/fig.html
  (no flag: pages 1-2 cut two ways, for "See it"; --full: the whole PDF and all its chunks, for sub-step 3;
   --kb: two made-up ServiceApps KB articles and all their chunks, from kb_chunk_sketch.chunk_article)
Then paste the output between ":::html" and ":::" in the deep dive and rebuild the blog.
"""
import html, sys
from pypdf import PdfReader
from app.rag.chunker import chunk_policy, load_pages, _SKIP
from app.services import policy as ps

p = ps.get_policy("73721"); path, _ = ps.policy_path("73721")
E = html.escape
HUES = ["#2b7de9", "#e8590c", "#2f9e44", "#ae3ec9", "#d6336c", "#1098ad", "#f59f00", "#5c7cfa"]
css = """<style>
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
</style>"""
out = ['<div class="cv">', css]

# --- Figure 1: what the code reads and skips (page 1 raw) -------------------------------------
raw = (PdfReader(str(path)).pages[0].extract_text() or "").splitlines()
out.append('<h4>1. What pypdf reads from page 1, and what the code throws away</h4>')
out.append('<div class="note">Struck-through lines are page furniture (same on every page). They are dropped before any chunking.</div><div class="doc">')
for l in raw[:9]:
    cls = "ln skip" if _SKIP.match(l.strip()) else "ln"
    out.append(f'<div class="{cls}">{E(l)}</div>')
out.append('<div class="ln skip" style="text-decoration:none">… (rest of page 1)</div></div>')

# --- Figure 2: cut by structure (real chunks, pages 1-2) --------------------------------------
chunks = [c for c in chunk_policy(path, p) if c.meta["page"] <= 2]
out.append('<h4>2. Cut by structure (what NurseOps Now does): pages 1–2 become 8 chunks</h4>')
out.append('<div class="note">Each colored box is one chunk, exactly as stored. The bold first line is the <b>header the code adds</b>; it is not in the PDF. '
           'The rest is the rule, word for word.</div><div class="doc">')
for k, c in enumerate(chunks):
    h = HUES[k % len(HUES)]
    hdr, body = c.text.split("\n", 1)
    if c.meta["label"] == "§2.A":
        out.append('<div class="gone"><div class="ln skip" style="text-decoration:none">2. Covered when ONE of the following is documented</div>'
                   '<div class="note" style="margin:2px 0">↑ This heading has no text of its own, so it is <b>not</b> a chunk. '
                   'Its title is copied into the header of each rule below (2.A–2.D), so every rule still says <i>covered when</i>.</div></div>')
    out.append(f'<div class="ck" style="--h:{h}"><span class="tag" style="background:{h}">Chunk {k+1} · {E(c.id)} · {E(c.meta["label"])} · page {c.meta["page"]} · {len(c.text)} chars</span>'
               f'<div class="hdr">{E(hdr)}</div><div class="ln">{E(body)}</div></div>')
out.append('</div>')

# --- Figure 3: cut every 500 characters (same text) -------------------------------------------
text = "\n".join(l for pg, ls in load_pages(path) if pg <= 2 for l in ls)
N = 500
pieces = [text[i:i + N] for i in range(0, len(text), N)]
out.append(f'<h4>3. Cut every 500 characters (the common way): the same text becomes {len(pieces)} pieces</h4>')
out.append('<div class="note">Same pages, no structure: a new piece starts every 500 characters, wherever that lands. '
           'The red ✂ marks each cut. No piece has a header, so nothing says which policy, version or page it came from.</div><div class="doc">')
for k, pc in enumerate(pieces):
    h = HUES[(k + 5) % len(HUES)]
    out.append(f'<div class="ck" style="--h:{h}"><span class="tag" style="background:{h}">Piece {k+1} · {len(pc)} chars · no header</span>'
               f'<div class="ln">{E(pc)}{"<span class=cut>✂</span>" if k < len(pieces)-1 else ""}</div></div>')
out.append('</div>')
out.append('<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk</span>'
           '<span><b style="font-family:ui-monospace,monospace">[…]</b> = header added by the code</span>'
           '<span><span class="skip">struck</span> = thrown away</span><span><span class="cut">✂</span> = where a 500-character cut lands</span></div>')
out.append('</div>')
FIG_TWO_WAYS = "\n".join(out)


def full_document(cpt: str = "73721") -> str:
    """'The whole PDF and all its chunks': every page as the PDF reader sees it, furniture struck through,
    each chunk's lines in one colored box (real chunker output). Used in deep dive 1, sub-step 3."""
    from app.rag.chunker import _CRITERION, _SECTION
    pol = ps.get_policy(cpt); pth, _ = ps.policy_path(cpt)
    chunks = chunk_policy(pth, pol)
    by_label = {c.meta["label"]: (k, c) for k, c in enumerate(chunks)}
    o = ['<div class="cv">', css.replace(".cv .key{", ".cv .page{border:1px solid var(--line);border-radius:8px;padding:8px 12px 4px;margin:12px 0;background:var(--bg)}"
         ".cv .pno{font:600 .8em/1.4 -apple-system,system-ui,sans-serif;color:var(--muted);margin:0 0 6px}"
         ".cv .strip{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 4px}.cv .strip a{color:#fff;text-decoration:none;font:600 .72em/1.7 -apple-system,system-ui,sans-serif;border-radius:9px;padding:0 7px}"
         ".cv .title{opacity:.7;font-style:italic}.cv .key{")]
    pages = PdfReader(str(pth)).pages
    o.append(f'<div class="note"><b>{E(pol["number"])} v{E(pol["version"])}, {E(pol["title"])}</b>: {len(pages)} pages → <b>{len(chunks)} chunks</b>. '
             'Click a chunk to jump to it.</div><div class="strip">')
    cur_pg = 0
    for k, c in enumerate(chunks):
        if c.meta["page"] != cur_pg:
            cur_pg = c.meta["page"]
            o.append(f'<span class="note" style="margin:0 2px 0 6px">p{cur_pg}</span>')
        o.append(f'<a href="#ck-{E(c.id)}" style="background:{HUES[k % len(HUES)]}">{E(c.meta["label"])}</a>')
    o.append('</div>')
    section, label = "", None
    for pno, page in enumerate(pages, 1):
        o.append(f'<div class="page"><div class="pno">PAGE {pno} OF {len(pages)}</div>')
        box_open = False
        for ln in (page.extract_text() or "").splitlines():
            s = ln.strip()
            if not s:
                continue
            if _SKIP.match(s):
                o.append(f'<div class="ln skip">{E(ln)}</div>')
                continue
            m_sec, m_crit = _SECTION.match(s), _CRITERION.match(s)
            new_label, is_title = None, False
            if m_sec:
                section = m_sec.group(1)
                new_label, is_title = f"§{section}", True
            elif m_crit and section:
                new_label = f"§{section}.{m_crit.group(1)}"
            if new_label:
                if box_open:
                    o.append('</div>'); box_open = False
                label = new_label
                if label not in by_label:          # heading with no body of its own: not a chunk
                    o.append(f'<div class="gone"><div class="ln">{E(ln)}</div><div class="note" style="margin:2px 0">'
                             f'↑ heading only, not a chunk: its title goes into the header of each rule below</div></div>')
                    continue
                k, c = by_label[label]
                h = HUES[k % len(HUES)]
                o.append(f'<div class="ck" id="ck-{E(c.id)}" style="--h:{h}"><span class="tag" style="background:{h}">'
                         f'Chunk {k + 1} of {len(chunks)} · {E(c.meta["label"])} · {len(c.text)} chars</span>'
                         f'<div class="hdr">{E(c.text.split(chr(10), 1)[0])}</div>')
                box_open = True
                if is_title:
                    o.append(f'<div class="ln title">{E(ln)}   ← title, goes into the header</div>')
                    continue
            o.append(f'<div class="ln">{E(ln)}</div>')
        if box_open:
            o.append('</div>')
        o.append('</div>')
    o.append('<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk (its lines from the PDF)</span>'
             '<span><b style="font-family:ui-monospace,monospace">[…]</b> = header the code adds</span>'
             '<span><span class="skip">struck</span> = thrown away</span><span><span class="title">italic</span> = section title, moved into the header</span></div></div>')
    return "\n".join(o)


# ---------------------------------------------------------------- ServiceApps KB articles (illustrative, --kb)

def _a(sys_id, num, title, kb, cat, html_body):
    """A KB article in the shape the Table API returns with sysparm_display_value=all."""
    v = lambda x: {"value": x, "display_value": x}
    return {"sys_id": v(sys_id), "number": v(num), "short_description": v(title), "text": v(html_body),
            "kb_knowledge_base": v(kb), "kb_category": v(cat), "sys_updated_on": v("2026-11-12 09:30:00"),
            "can_read_user_criteria": v("all-employees")}


KB_ARTICLES = [
    _a("a1", "KB0010234", "Connect to the company VPN on macOS", "IT Software", "Network › VPN", """
<p class="kb-banner">Internal: do not share outside the company.</p>
<h2>Symptoms</h2>
<p>The VPN client won't connect, or connects and drops after a few seconds.</p>
<h2>Applies to</h2>
<ul><li>macOS 14 and later</li><li>Company VPN client 6.x</li></ul>
<h2>Steps</h2>
<ol><li>Open the VPN client from the menu bar.</li><li>Enter the portal address vpn.example.com.</li>
<li>Sign in with your company account and approve the MFA prompt.</li><li>Wait until the status shows Connected.</li>
<li>If it fails, quit the client and sign in again.</li><li>Still failing: find your error code below.</li></ol>
<h2>Error codes</h2>
<table><tr><th>Code</th><th>Meaning and fix</th></tr>
<tr><td>Error 809</td><td>Error 809 means the VPN can't reach the server. Check that you are not on a guest Wi-Fi network, then restart the VPN client. If it continues, open an incident with category Network › VPN and attach the client log.</td></tr>
<tr><td>Error 812</td><td>Error 812 means your account isn't in the VPN access group. Request "VPN access" in the service catalog.</td></tr>
<tr><td>Error 619</td><td>Error 619 means the connection timed out. Switch networks or restart your Mac, then try again.</td></tr></table>
<h2>Related articles</h2>
<ul><li>KB0010199 Reset your MFA device</li><li>KB0010240 Connect to the VPN on Windows</li></ul>
<p class="kb-feedback">Was this article helpful? Yes / No</p>
"""),
    _a("b2", "KB0020311", "Remote work policy", "HR Policies", "Workplace", """
<p class="kb-banner">Internal: do not share outside the company.</p>
<h2>1. Purpose</h2>
<p>Sets out when employees may work away from the office.</p>
<h2>2. Eligibility</h2>
<p>Employees who have passed their probation period may work remotely up to 3 days a week, with their manager's agreement. Roles that need on-site equipment are excluded.</p>
<h2>3. Equipment and security</h2>
<p>Use a company laptop and connect through the company VPN. Do not work from public Wi-Fi without the VPN.</p>
<h2>4. Working from another country</h2>
<p>Employees may work from another country for up to 10 working days a year. Longer stays need written approval from HR and Payroll before travel, because of tax and visa rules.</p>
<h2>5. Expenses</h2>
<p>Home internet and furniture are not reimbursed. A one-time equipment allowance is available; see the expense policy.</p>
<h2>6. Requesting an exception</h2>
<p>Submit an "HR exception request" in the HR portal at least 15 working days before the start date.</p>
<p class="kb-feedback">Was this article helpful? Yes / No</p>
"""),
]


def kb_figure() -> str:
    """Each made-up article whole, with every chunk chunk_article() makes from it, in color."""
    import kb_chunk_sketch as kbs
    o = ['<div class="cv">', css.replace(".cv .key{", ".cv .page{border:1px solid var(--line);border-radius:8px;padding:8px 12px 4px;margin:12px 0;background:var(--bg)}"
         ".cv .pno{font:600 .8em/1.4 -apple-system,system-ui,sans-serif;color:var(--muted);margin:0 0 6px}"
         ".cv .title{opacity:.7;font-style:italic}.cv .key{")]
    for n_art, a in enumerate(KB_ARTICLES, 1):
        chunks = kbs.chunk_article(a)
        num, title = a["number"]["value"], a["short_description"]["value"]
        kind = "tech / software" if n_art == 1 else "domain: HR policy"
        o.append(f'<h4>Article {n_art} ({kind}): {E(num)} {E(title)} → {len(chunks)} chunks</h4>')
        o.append(f'<div class="page"><div class="pno">{E(num)} · KB: {E(a["kb_knowledge_base"]["display_value"])} · '
                 f'Category: {E(a["kb_category"]["display_value"])} · Published</div>')
        p = kbs.Blocks(); p.feed(a["text"]["value"])
        heading, k, open_box, shown = "Overview", -1, False, []
        def close():
            nonlocal open_box
            if open_box:
                o.append('</div>'); open_box = False
        def box(h, first_line=None):
            nonlocal k, open_box
            k += 1; c = chunks[k]; col = HUES[(k + 2 * n_art) % len(HUES)]
            o.append(f'<div class="ck" style="--h:{col}"><span class="tag" style="background:{col}">Chunk {k + 1} of {len(chunks)} · '
                     f'{E(h)} · {len(c["text"])} chars</span><div class="hdr">{E(c["text"].split(chr(10), 1)[0])}</div>')
            if first_line:
                o.append(f'<div class="ln title">{E(first_line)}   ← heading, goes into the header</div>')
            open_box = True
            shown.append(c["text"])
        # Walk the same blocks units() walks, so each colored box is exactly one chunk.
        has_text = {h for h, _ in kbs.units(a["text"]["value"])}
        for b in p.blocks:
            if b[0] == "skip":
                close(); o.append(f'<div class="ln skip">{E(b[1])}</div>')
            elif b[0] == "heading":
                close(); heading = b[1]
                if heading in kbs.SKIP_SECTIONS:
                    o.append(f'<div class="ln skip">{E(heading)}</div>')
                elif heading in has_text and any(x[0] == "line" for x in p.blocks[p.blocks.index(b) + 1:][:1]):
                    box(heading, heading)
                else:
                    o.append(f'<div class="gone"><div class="ln">{E(heading)}</div><div class="note" style="margin:2px 0">'
                             '↑ heading only, not a chunk: each table row below is its own chunk, named by its first cell</div></div>')
            elif heading in kbs.SKIP_SECTIONS:
                o.append(f'<div class="ln skip">{E(b[1])}</div>')
            elif b[0] == "line":
                o.append(f'<div class="ln">{E(b[1])}</div>')
            elif b[0] == "row":
                close()
                if b[2]:
                    o.append(f'<div class="ln title">{E(" | ".join(b[1]))}   ← table header row, not a chunk</div>')
                else:
                    box(b[1][0]); o.append(f'<div class="ln">{E(b[1][0])} | {E(" ".join(b[1][1:]))}</div>'); close()
        close()
        o.append('</div>')
        assert len(shown) == len(chunks), (num, len(shown), len(chunks))
    o.append('<div class="key"><span><span class="sw" style="background:#2b7de9"></span>colored box = one chunk</span>'
             '<span><b style="font-family:ui-monospace,monospace">[…]</b> = header the code adds</span>'
             '<span><span class="skip">struck</span> = thrown away (template text, links-only section)</span>'
             '<span><span class="title">italic</span> = heading, moved into the header</span></div></div>')
    return "\n".join(o)


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    print(kb_figure() if "--kb" in sys.argv else full_document() if "--full" in sys.argv else FIG_TWO_WAYS)
