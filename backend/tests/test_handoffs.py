"""One end-to-end mocked test per README handoff script (W1, W2). Keep in step with README.

The check after intake is the mock AI (AI-MK) on the real sample PDFs.
"""
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import new_session
from app.models import utcnow
from app.repositories import cases as repo

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


@pytest.fixture
def client(env, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "manifest.json", env / "samples" / "manifest.json")
    for f in SAMPLES.glob("*.pdf"):
        shutil.copy(f, env / "samples" / f.name)
    from app.main import app
    from app.services import auth
    s = new_session(); auth.seed_reviewers(s); s.commit(); s.close()
    with TestClient(app) as c:
        yield c


def login(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "test-pass"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def decide(client, h, cid, action, rationale="reason"):
    return client.post(f"/api/cases/{cid}/decision", headers=h, json={"action": action, "rationale": rationale})


def check_inbox(client):
    """Reset fills the queue: the 3 requests arrive and get their AI-MK review."""
    r = client.post("/api/demo/reset", headers=login(client, "meddir"))
    assert r.status_code == 200
    summary = r.json()["summary"]
    assert summary["new"] == 3 and summary["engine"] == "AI-MK"
    intake = login(client, "intake1")
    assert client.post("/api/intake/poll", headers=intake).json()["created"] == 0   # nothing left in the inbox
    ids = {c["filename"]: c["id"] for c in client.get("/api/cases", headers=intake).json()}
    return intake, ids, summary


def test_w1_complete_request_to_decision(client):
    intake, ids, summary = check_inbox(client)
    a, c = ids["72148_a_complete.pdf"], ids["70551_c_not_met.pdf"]
    nurse1, meddir = login(client, "nurse1"), login(client, "meddir")
    assert summary["ready_by_tier"] == {"likely_approve": 1, "likely_deny": 1}

    # negatives: no login 401, wrong role 403
    assert client.post(f"/api/cases/{a}/decision", json={"action": "Approve", "rationale": "x"}).status_code == 401
    assert decide(client, intake, a, "Approve").status_code == 403

    # happy path: AI-MK says likely approve -> nurse1 approves -> Synced
    detail = client.get(f"/api/cases/{a}", headers=nurse1).json()
    assert detail["status"] == "ReadyForReview" and detail["tier"] == "likely_approve"
    assert detail["ai_label"] == "AI-MK" and detail["ai_review"]["fields"]["cpt"] == "72148"
    assert detail["description"].endswith("Lumbar radiculopathy (M54.16)")
    r = decide(client, nurse1, a, "Approve", "8 weeks PT documented, radiculopathy")
    assert r.status_code == 200 and r.json()["status"] == "Synced" and r.json()["override"] is False
    assert client.get("/api/metrics", headers=meddir).json()["cases_reviewed"] == 1

    # alternate: AI-MK says likely deny -> nurse1 can't deny, pends -> meddir denies
    assert client.get(f"/api/cases/{c}", headers=nurse1).json()["tier"] == "likely_deny"
    assert decide(client, nurse1, c, "Deny", "no red flags").status_code == 403
    assert decide(client, nurse1, c, "Pend", "Needs MD review: headache, no red flags").json()["status"] == "Pended"
    assert decide(client, meddir, c, "Deny", "No red flags; tension-type headache").json()["status"] == "Synced"
    actors = [(x["actor"], x["details"].get("decision")) for x in
              client.get(f"/api/cases/{c}", headers=meddir).json()["audit"] if x["action"] == "decision"]
    assert actors == [("nurse1", "Pended"), ("meddir", "Denied")]


def test_w2_incomplete_docs_arrive_then_decision(client):
    intake, ids, summary = check_inbox(client)
    b = ids["73721_b_missing_pt.pdf"]
    nurse1, nurse2 = login(client, "nurse1"), login(client, "nurse2")
    assert [i["id"] for i in summary["incomplete"]] == [b]

    detail = client.get(f"/api/cases/{b}", headers=nurse1).json()
    assert detail["status"] == "Incomplete" and detail["allowed_actions"] == []
    assert detail["ai_review"]["missing"][0]["item"].startswith("Physical therapy records")
    sent = [x for x in detail["audit"] if x["action"] == "provider_request_sent"]
    assert sent and sent[0]["details"]["message"].startswith("Dear Dr. Okafor")
    assert decide(client, nurse1, b, "Approve").status_code == 409  # negative: wrong status

    # alternate: provider doesn't respond -> stuck after 2 days
    s = new_session(); repo.get_case(s, b).status_changed_at = utcnow() - timedelta(days=3); s.commit(); s.close()
    assert [x["id"] for x in client.get("/api/stuck?days=2", headers=nurse1).json()] == [b]

    # happy path: intake adds PT notes -> AI-MK reviews again -> Ready -> nurse2 approves
    pt = (SAMPLES / "followup" / "73721_b_followup_pt_notes.pdf").read_bytes()
    r = client.post(f"/api/cases/{b}/documents", headers=intake,
                    files={"file": ("73721_b_followup_pt_notes.pdf", pt, "application/pdf")})
    assert r.json()["status"] == "ReadyForReview" and r.json()["tier"] == "likely_approve"
    assert decide(client, intake, b, "Approve").status_code == 403  # negative: wrong role
    assert decide(client, nurse2, b, "Approve", "PT notes show 6 weeks, knee still catching").json()["status"] == "Synced"
    statuses = [x["details"]["to"] for x in client.get(f"/api/cases/{b}", headers=nurse2).json()["audit"]
                if x["action"] == "status_change"]
    assert statuses == ["Incomplete", "Received", "ReadyForReview", "Approved", "Synced"]
