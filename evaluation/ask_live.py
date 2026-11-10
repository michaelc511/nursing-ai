"""Live check of the Claude review (needs ANTHROPIC_API_KEY in .env). Costs real money (~$0.05-0.15 per case).

Run from backend/:  AI_MODE=claude python ../evaluation/ask_live.py [72148_a_complete.pdf]
Reviews one sample request in a throwaway database and prints tier, criteria, warnings, tokens, cost, latency.
"""
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ.update(DATABASE_URL=f"sqlite:///{tmp / 'live.db'}", STORAGE_DIR=str(tmp / "storage"),
                  INBOX_DIR=str(tmp / "inbox"), AI_MODE="claude")
(tmp / "inbox").mkdir()

from app.db import init_db, new_session  # noqa: E402
from app.llm import client as llm  # noqa: E402
from app.services import intake, review  # noqa: E402

if not llm.has_key():
    sys.exit("No ANTHROPIC_API_KEY in .env: add it first (never paste it in chat).")
name = sys.argv[1] if len(sys.argv) > 1 else "72148_a_complete.pdf"
shutil.copy(ROOT / "data" / "samples" / name, tmp / "inbox")
init_db()
s = new_session()
c = intake.poll_inbox(s, actor="ask_live")[0]
r = review.review_case(s, c.id, actor="ask_live")
s.commit()
res = r.result
print(f"Case {c.id} {name}: tier={r.tier} status={c.status} engine={res['engine']}")
print("Summary:", res["summary"])
for cr in res["criteria"]:
    ok = all(e["verified"] for e in cr["request_evidence"]) if cr["request_evidence"] else None
    print(f"  - {cr['result']:8} {cr['criterion'][:80]}  quotes verified={ok}")
for m in res["missing"]:
    print(f"  missing: {m['item']} ({m['why'][:60]})")
for w in res["warnings"]:
    print(f"  WARNING: {w}")
print("Usage:", llm.totals(s, case_id=c.id))
