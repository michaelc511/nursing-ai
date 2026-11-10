"""Layer 3: policy knowledge. CPT code -> policy (registry in backend/policies/index.json).

Phase 2.5: list, view and download policy PDFs. Phase 3: RAG over the same PDFs (app/rag/):
clause-aware chunks with metadata, sentence-transformers embeddings, Chroma, search within
the CPT's policy only. Policies only, never patient documents.
"""
import json
from pathlib import Path

from app.config import BACKEND
from app.errors import NotFound
from app.models import Case

POLICY_DIR = BACKEND / "policies"


def registry() -> list[dict]:
    try:
        return json.loads((POLICY_DIR / "index.json").read_text())
    except (OSError, ValueError):
        return []


def list_policies() -> list[dict]:
    return [{k: p[k] for k in ("cpt", "title", "number", "version", "effective", "codes")} for p in registry()]


def get_policy(cpt: str) -> dict:
    for p in registry():
        if p["cpt"] == cpt:
            return p
    raise NotFound(f"No policy for CPT {cpt}")


def policy_path(cpt: str) -> tuple[Path, str]:
    p = get_policy(cpt)
    path = (POLICY_DIR / p["file"]).resolve()
    if POLICY_DIR.resolve() not in path.parents or not path.exists():
        raise NotFound(f"Policy file missing for CPT {cpt}")
    return path, f"{p['number']}_{p['title'].replace(' ', '_')}_v{p['version']}.pdf"


def cpt_for_case(case: Case) -> str | None:
    """CPT read from the form by the review (#2a); before a review, the file name prefix (demo)."""
    if case.cpt:
        return case.cpt
    cpt = case.filename[:5]
    return cpt if cpt.isdigit() else None


def policy_for_case(case: Case) -> dict | None:
    cpt = cpt_for_case(case)
    if not cpt:
        return None
    try:
        p = get_policy(cpt)
    except NotFound:
        return None
    return {k: p[k] for k in ("cpt", "title", "number", "version", "effective")}


# ---------------------------------------------------------------- Phase 3: RAG (F3, S14, S4, N2)

REVIEW_QUERY = "coverage criteria conservative therapy red flags required documentation"


def index_policies() -> dict:
    from app.rag import index
    return index.index_all()


def search(query: str, cpt: str | None = None, k: int = 4) -> list[dict]:
    """Top-k policy chunks; builds the index on first use so a fresh checkout just works."""
    from app.rag import index
    if cpt:
        get_policy(cpt)                       # 404 for an unknown CPT
    if index.count() == 0:
        index.index_all()
    return index.search(query, cpt=cpt, k=k)


def chunks(cpt: str) -> list[dict]:
    from app.rag import index
    return [{"id": c.id, "label": c.meta["label"], "section_title": c.meta["section_title"],
             "page": c.meta["page"], "text": c.text} for c in index.chunks_for(cpt)]


def criteria_for_review(cpt: str, request_text: str = "") -> list[dict]:
    """Policy chunks the AI review reads (CLAUDE.md data flow: 'Claude reads blob + RAG policy chunks')."""
    query = f"{REVIEW_QUERY} {request_text[:600]}".strip()
    return search(query, cpt=cpt, k=6)
