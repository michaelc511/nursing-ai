"""Retrieval-only eval (no LLM): hit@1 and hit@3 on the golden retrieval questions.

Run from backend/:  python ../evaluation/run_retrieval.py   (Phase 7 decides hybrid/re-rank on this)
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from app.services import policy  # noqa: E402

rows = [json.loads(l) for l in (pathlib.Path(__file__).parent / "golden.jsonl").read_text().splitlines() if l.strip()]
rows = [r for r in rows if r["type"] == "retrieval"]
h1 = h3 = n = 0
for r in rows:
    hits = policy.search(r["question"], cpt=r["cpt"], k=3)
    if r["expect_label"] is None:
        ok = (hits[0]["score"] if hits else 0) <= r["max_score"]
        print(f"{'PASS' if ok else 'FAIL'} {r['id']} off-topic top score {hits[0]['score'] if hits else '-'}")
        continue
    n += 1
    labels = [h["label"] for h in hits]
    h1 += labels[:1] == [r["expect_label"]]
    h3 += r["expect_label"] in labels
    print(f"{'HIT1' if labels[:1] == [r['expect_label']] else ('HIT3' if r['expect_label'] in labels else 'MISS')} "
          f"{r['id']} want {r['expect_label']} got {labels}")
print(f"\nhit@1 {h1}/{n} = {h1 / n:.0%}   hit@3 {h3}/{n} = {h3 / n:.0%}")
