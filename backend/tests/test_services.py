from datetime import timedelta

import pytest

from app.errors import AppError, Forbidden, InvalidTransition, Unauthorized
from app.models import AIReview, utcnow
from app.repositories import cases as repo
from app.services import auth, cases, decision, demo, intake


@pytest.fixture
def reviewers(session):
    auth.seed_reviewers(session)
    return {u: repo.get_reviewer_by_username(session, u) for u in ("nurse1", "nurse2", "meddir", "intake1")}


def ready_case(session, tier=None):
    c = intake.create_case_from_bytes(session, "a.pdf", b"%PDF-1.4 test")
    if tier:
        repo.add(session, AIReview(case_id=c.id, result={"tier": tier}, tier=tier))
    demo.mark(session, c.id, "ready")
    return c


# login
def test_seed_and_login_each_role(session, reviewers):
    assert {r.role for r in reviewers.values()} == {"nurse", "medical_director", "intake"}
    for u in reviewers:
        token, r = auth.login(session, u, "test-pass")
        assert auth.user_from_token(session, token).username == u


def test_wrong_password_rejected(session, reviewers):
    with pytest.raises(Unauthorized):
        auth.login(session, "nurse1", "nope")


def test_seed_is_rerunnable(session, reviewers):
    assert auth.seed_reviewers(session) == 0


# intake
def test_poll_creates_received_cases_and_empties_inbox(session, env):
    (env / "inbox" / "fax1.pdf").write_bytes(b"%PDF-1.4 a")
    (env / "inbox" / "notes.txt").write_text("ignored")
    created = intake.poll_inbox(session)
    assert len(created) == 1 and created[0].status == "Received"
    assert not (env / "inbox" / "fax1.pdf").exists()
    path, name = cases.document_path(session, created[0].id)
    assert path.read_bytes() == b"%PDF-1.4 a" and name == "fax1.pdf"


def test_unsupported_upload_rejected(session):
    with pytest.raises(AppError):
        intake.create_case_from_bytes(session, "x.exe", b"bad")


def test_new_docs_move_incomplete_to_received(session):
    c = intake.create_case_from_bytes(session, "b.pdf", b"%PDF")
    demo.mark(session, c.id, "incomplete")
    intake.add_documents(session, c.id, "pt_notes.pdf", b"%PDF pt")
    assert c.status == "Received"
    assert cases.document_path(session, c.id, 1)[1] == "pt_notes.pdf"


def test_incomplete_sends_provider_request(session):
    c = intake.create_case_from_bytes(session, "b.pdf", b"%PDF")
    demo.mark(session, c.id, "incomplete")
    actions = [a.action for a in repo.audit_for_case(session, c.id)]
    assert "provider_request_sent" in actions


# decisions
@pytest.mark.parametrize("user", ["nurse1", "meddir"])
def test_approve_syncs_and_audits(session, reviewers, user):
    c = ready_case(session)
    d = decision.decide(session, c.id, reviewers[user], "Approve", "Meets 6-week PT criterion")
    assert d.decision == "Approved" and c.status == "Synced" and c.sync_status == "synced"
    actions = [a.action for a in repo.audit_for_case(session, c.id)]
    assert {"decision", "synced"} <= set(actions)
    dec_row = next(a for a in repo.audit_for_case(session, c.id) if a.action == "decision")
    assert dec_row.actor == user


def test_rationale_required(session, reviewers):
    c = ready_case(session)
    with pytest.raises(AppError):
        decision.decide(session, c.id, reviewers["nurse1"], "Approve", "   ")
    assert c.status == "ReadyForReview"


def test_cannot_decide_received_case(session, reviewers):
    c = intake.create_case_from_bytes(session, "a.pdf", b"%PDF")
    with pytest.raises(InvalidTransition):
        decision.decide(session, c.id, reviewers["nurse1"], "Approve", "ok")


def test_non_reviewer_cannot_decide(session, reviewers):
    c = ready_case(session)
    with pytest.raises(Forbidden):
        decision.decide(session, c.id, None, "Approve", "ok")


def test_pend_then_decide(session, reviewers):
    c = ready_case(session)
    decision.decide(session, c.id, reviewers["nurse1"], "Pend", "Waiting on imaging report")
    assert c.status == "Pended"
    decision.decide(session, c.id, reviewers["meddir"], "Deny", "Criteria not met")
    assert c.status == "Synced"


@pytest.mark.parametrize("tier,action,override", [
    ("likely_deny", "Approve", True), ("likely_approve", "Deny", True),
    ("likely_approve", "Approve", False), ("needs_review", "Deny", False), (None, "Approve", False)])
def test_override_flag(session, reviewers, tier, action, override):
    c = ready_case(session, tier)
    who = "meddir" if action == "Deny" else "nurse1"
    assert decision.decide(session, c.id, reviewers[who], action, "reason").override is override


# metrics / stuck
def test_metrics(session, reviewers):
    a = ready_case(session, "likely_deny")
    decision.decide(session, a.id, reviewers["nurse1"], "Approve", "PT documented")
    b = intake.create_case_from_bytes(session, "b.pdf", b"%PDF")
    demo.mark(session, b.id, "incomplete")
    m = cases.metrics(session)
    assert m["total_cases"] == 2 and m["cases_reviewed"] == 1
    assert m["rework_rate"] == 0.5 and m["override_rate"] == 1.0
    assert m["avg_turnaround_days"] is not None


def test_stuck_cases(session):
    old = intake.create_case_from_bytes(session, "old.pdf", b"%PDF")
    old.status_changed_at = utcnow() - timedelta(days=3)
    intake.create_case_from_bytes(session, "new.pdf", b"%PDF")
    rows = cases.stuck(session, 2)
    assert [r["id"] for r in rows] == [old.id] and rows[0]["days_in_status"] >= 3


# reset-demo
def test_reset_demo_needs_demo_mode(session):
    with pytest.raises(AppError):
        demo.reset_demo(session)


def test_reset_demo_wipes_and_reloads(session, env, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    (env / "samples" / "72148_a_complete.pdf").write_bytes(b"%PDF a")
    intake.create_case_from_bytes(session, "x.pdf", b"%PDF")
    r = demo.reset_demo(session)
    assert repo.list_cases(session) == [] and r["inbox"] == ["72148_a_complete.pdf"]
    assert (env / "inbox" / "72148_a_complete.pdf").exists()
    assert repo.get_reviewer_by_username(session, "meddir") is not None


def test_queue_row_has_doc_id_and_description(session):
    c = intake.create_case_from_bytes(session, "72148_a_complete.pdf", b"%PDF", source="fax")
    row = cases.summary(session, c)
    assert row["doc_id"] == f"FAX-{c.received_at:%Y%m%d}-{c.id:04d}"
    assert row["description"] == "MRI lumbar spine (CPT 72148)"
    other = intake.create_case_from_bytes(session, "scan.pdf", b"%PDF")
    assert cases.summary(session, other)["description"].startswith("Prior auth request")


def test_poll_uses_channel_from_sample_manifest(session, env):
    (env / "samples" / "manifest.json").write_text(
        '{"b.pdf": {"channel": "portal", "diagnosis": "Sciatica (M54.41)"}, "c.pdf": "upload", "d.pdf": {"channel": "carrier-pigeon"}}')
    for n in ("a.pdf", "b.pdf", "c.pdf", "d.pdf"):
        (env / "inbox" / n).write_bytes(b"%PDF")
    got = {c.filename: (c.source, cases.summary(session, c)["doc_id"][:3]) for c in intake.poll_inbox(session)}
    assert got == {"a.pdf": ("fax", "FAX"), "b.pdf": ("portal", "PRT"), "c.pdf": ("upload", "UPL"), "d.pdf": ("fax", "FAX")}
    b = next(c for c in repo.list_cases(session) if c.filename == "b.pdf")
    assert cases.summary(session, b)["description"].endswith("· Sciatica (M54.41)")


def test_policy_lookup_by_cpt(session):
    from app.services import policy
    assert [p["cpt"] for p in policy.list_policies()] == ["72148", "73721", "70551"]
    knee = intake.create_case_from_bytes(session, "73721_b_missing_pt.pdf", b"%PDF")
    assert policy.policy_for_case(knee)["title"] == "MRI knee"
    assert cases.detail(session, knee.id)["policy"]["number"] == "RHP-IMG-022"
    unknown = intake.create_case_from_bytes(session, "scan.pdf", b"%PDF")
    assert policy.policy_for_case(unknown) is None
    path, name = policy.policy_path("70551")
    assert path.read_bytes().startswith(b"%PDF") and name.endswith("_v4.0.pdf")
    with pytest.raises(Exception):
        policy.policy_path("99999")


def test_poll_follows_manifest_order(session, env):
    (env / "samples" / "manifest.json").write_text('{"_note": "x", "z.pdf": "fax", "a.pdf": "portal"}')
    for n in ("a.pdf", "m.pdf", "z.pdf"):
        (env / "inbox" / n).write_bytes(b"%PDF")
    assert [c.filename for c in intake.poll_inbox(session)] == ["z.pdf", "a.pdf", "m.pdf"]


def test_only_medical_director_can_deny(session, reviewers):
    c = ready_case(session)
    with pytest.raises(Forbidden):
        decision.decide(session, c.id, reviewers["nurse1"], "Deny", "Criteria not met")
    assert c.status == "ReadyForReview"
    assert decision.decide(session, c.id, reviewers["meddir"], "Deny", "Criteria not met").decision == "Denied"
