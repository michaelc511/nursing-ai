"""ServiceApps KB sketch for deep dive 1 (ingestion): pull, hash and chunk knowledge-base articles.

Illustrative: no ServiceApps instance is connected to NurseOps Now. fetch_published() has never been run;
content_hash() and chunk_article() run locally on the two made-up articles in make_chunk_figure.py (--kb).
Same idea as backend/app/rag/chunker.py: the article's own structure decides where to cut.
"""
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
