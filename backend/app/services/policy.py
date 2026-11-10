"""Layer 3: policy knowledge. CPT code -> policy (registry in backend/policies/index.json).

Phase 2.5: list, view and download policy PDFs. Phase 3 adds RAG over the same PDFs.
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
    """Until Phase 3 the CPT comes from the file name prefix; then Claude extracts it from the request."""
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
