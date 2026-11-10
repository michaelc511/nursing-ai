"""Layer 3 RAG, step 1-3: load a policy PDF -> clause-aware chunks (S14) -> metadata (S4).

One chunk per policy clause: each lettered criterion (2.A, 2.B ...) or each numbered section
(Purpose, Required documentation, Not medically necessary, Review). Every chunk starts with a
contextual header saying whose rule it is, so a chunk read alone (by Claude or a nurse) still
names the policy, CPT code, version and section. Over-long clauses fall back to a recursive split.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

MAX_CHARS = 1200      # recursive fallback above this
OVERLAP = 150

# Page furniture repeated on every page: not policy content.
_SKIP = re.compile(r"^(REGIONAL HEALTH PLAN .*PAGE \d+/\d+|SYNTHETIC DEMO POLICY .*|Medical Policy: .*"
                   r"|Policy number: .*|Effective date: .*|CPT codes: .*)$")
_SECTION = re.compile(r"^(\d+)\.\s+(.+)$")          # "2. Covered when ONE of the following is documented"
_CRITERION = re.compile(r"^([A-H])\.\s+(.+)$")      # "A. Low back pain ..."

# Injection-like text inside a document must never reach the index unflagged.
INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above) instructions|^\s*system\s*:"
                       r"|you are now|disregard (the|your) (rules|instructions)", re.I | re.M)


@dataclass
class Chunk:
    id: str
    text: str                      # header + clause body (what gets embedded and shown)
    meta: dict = field(default_factory=dict)


def load_pages(path: Path) -> list[tuple[int, list[str]]]:
    """[(page_no, content lines)] with page headers/footers removed."""
    out = []
    for i, page in enumerate(PdfReader(str(path)).pages, start=1):
        lines = [ln.rstrip() for ln in (page.extract_text() or "").splitlines()]
        out.append((i, [ln for ln in lines if ln.strip() and not _SKIP.match(ln.strip())]))
    return out


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
                    cur = cur[-OVERLAP:] + sep + p
                else:
                    cur = cand
            out.append(cur)
            return [s for piece in out for s in _split_long(piece)] if any(len(o) > MAX_CHARS for o in out) else out
    return [text[i:i + MAX_CHARS] for i in range(0, len(text), MAX_CHARS - OVERLAP)]


def chunk_policy(path: Path, policy: dict) -> list[Chunk]:
    """policy = one row of policies/index.json (cpt, title, number, version, effective)."""
    clauses: list[dict] = []          # {section, section_title, criterion, page, lines}
    cur = None
    section, section_title = "", ""
    for page_no, lines in load_pages(path):
        for ln in lines:
            s = ln.strip()
            m_sec, m_crit = _SECTION.match(s), _CRITERION.match(s)
            if m_sec:
                section, section_title = m_sec.group(1), m_sec.group(2)
                cur = {"section": section, "section_title": section_title, "criterion": "",
                       "page": page_no, "lines": []}
                clauses.append(cur)
            elif m_crit and section:
                cur = {"section": section, "section_title": section_title, "criterion": m_crit.group(1),
                       "page": page_no, "lines": [m_crit.group(2)]}
                clauses.append(cur)
            elif cur is not None:
                cur["lines"].append(s)
    # A section heading followed only by lettered criteria carries no body of its own.
    clauses = [c for c in clauses if c["lines"]]

    chunks: list[Chunk] = []
    for c in clauses:
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
    return chunks


def body_of(chunk_text: str) -> str:
    """Chunk text without its contextual header (the quotable policy wording)."""
    return chunk_text.split("\n", 1)[1] if chunk_text.startswith("[") and "\n" in chunk_text else chunk_text
