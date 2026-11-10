"""Layer 2 with the mock engine (AI-MK) on the real sample PDFs."""
import json
import shutil
from pathlib import Path

import pytest

from app.models import AIReview
from app.repositories import cases as repo
from app.services import auth, decision, intake, review

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


@pytest.fixture
def samples(env):
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "manifest.json", env / "samples" / "manifest.json")
    for f in SAMPLES.glob("*.pdf"):
        shutil.copy(f, env / "inbox" / f.name)
    return env


def by_file(session):
    return {c.filename: c for c in repo.list_cases(session)}


def test_run_all_reviews_every_new_case(session, samples):
    s = review.run_all(session, actor="cowork", trigger="test")
    assert s["new"] == 3 and s["reviewed"] == 3 and s["engine"] == "AI-MK"
    assert [i["missing"] for i in s["incomplete"]] == ["Physical therapy records (dates and response)"]
    assert s["ready_by_tier"] == {"likely_approve": 1, "likely_deny": 1}
    c = by_file(session)
    assert c["72148_a_complete.pdf"].status == "ReadyForReview"
    assert c["73721_b_missing_pt.pdf"].status == "Incomplete"
    assert c["70551_c_not_met.pdf"].status == "ReadyForReview"
    assert review.last_run(session)["trigger"] == "test"


def test_review_reads_cpt_and_diagnosis_and_verifies_quotes(session, samples):
    review.run_all(session, actor="t", trigger="t")
    a = by_file(session)["72148_a_complete.pdf"]
    r = repo.latest_review(session, a.id)
    assert a.cpt == "72148" and a.diagnosis == "Lumbar radiculopathy (M54.16)"
    assert r.result["engine"] == "AI-MK" and r.tier == "likely_approve" and r.result["warnings"] == []
    quotes = [e for c in r.result["criteria"] for e in c["request_evidence"]]
    assert quotes and all(e["verified"] for e in quotes)
    assert all(c["policy_evidence"]["verified"] for c in r.result["criteria"])
    actors = {x.actor for x in repo.audit_for_case(session, a.id) if x.action in ("ai_review", "status_change")}
    assert actors == {"AI-MK"}


def test_incomplete_case_sends_the_drafted_request(session, samples):
    review.run_all(session, actor="t", trigger="t")
    b = by_file(session)["73721_b_missing_pt.pdf"]
    sent = [x for x in repo.audit_for_case(session, b.id) if x.action == "provider_request_sent"]
    assert sent and sent[0].details["message"].startswith("Dear Dr. Okafor")


def test_added_documents_are_reviewed_again(session, samples):
    review.run_all(session, actor="t", trigger="t")
    b = by_file(session)["73721_b_missing_pt.pdf"]
    pt = (SAMPLES / "followup" / "73721_b_followup_pt_notes.pdf").read_bytes()
    intake.add_documents(session, b.id, "73721_b_followup_pt_notes.pdf", pt)
    r = review.review_case(session, b.id, actor="intake1")
    assert b.status == "ReadyForReview" and r.tier == "likely_approve" and r.result["warnings"] == []
    assert any(e["doc"] == 1 and e["verified"] for c in r.result["criteria"] for e in c["request_evidence"])


def test_bad_quote_forces_needs_review(session, samples):
    f = samples / "samples" / "mock_reviews" / "72148_a_complete.json"
    data = json.loads(f.read_text())
    data["criteria"][0]["request_evidence"][0]["quote"] = "Patient has had pain for 2 years."
    f.write_text(json.dumps(data))
    review.run_all(session, actor="t", trigger="t")
    r = repo.latest_review(session, by_file(session)["72148_a_complete.pdf"].id)
    assert r.tier == "needs_review" and any("Quote not found" in w for w in r.result["warnings"])


def test_unknown_document_goes_to_a_human(session, samples):
    c = intake.create_case_from_bytes(session, "scan.pdf", b"not really a pdf")
    r = review.review_case(session, c.id, actor="t")
    assert r.tier == "needs_review" and c.status == "ReadyForReview"
    assert not [x for x in repo.audit_for_case(session, c.id) if x.action == "provider_request_sent"]


def test_ai_never_decides(session, samples):
    auth.seed_reviewers(session)
    review.run_all(session, actor="t", trigger="t")
    c = by_file(session)["70551_c_not_met.pdf"]
    assert repo.latest_review(session, c.id).tier == "likely_deny" and c.status == "ReadyForReview"
    review.review_case(session, c.id, actor="t")          # re-review: no status change past Received
    assert c.status == "ReadyForReview"
    meddir = repo.get_reviewer_by_username(session, "meddir")
    d = decision.decide(session, c.id, meddir, "Deny", "No red flags; tension-type headache")
    assert d.ai_tier == "likely_deny" and d.override is False
