"""One end-to-end mocked test per README handoff script (W1, W2). Keep in step with README."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import new_session
from app.models import utcnow
from app.repositories import cases as repo
from app.services import auth, demo


@pytest.fixture
def client(env, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    for name in ("72148_a_complete.pdf", "73721_b_missing_pt.pdf", "70551_c_not_met.pdf"):
        (env / "samples" / name).write_bytes(b"%PDF-1.4 " + name.encode())
    from app.main import app
    with TestClient(app) as c:
        yield c


def login(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "test-pass"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def cli(fn, *args, **kw):
    """Run a CLI-level service call (ops step) in its own committed session."""
    s = new_session()
    try:
        out = fn(s, *args, **kw)
        s.commit()
        return out
    finally:
        s.close()


def decide(client, h, cid, action, rationale="reason"):
    return client.post(f"/api/cases/{cid}/decision", headers=h, json={"action": action, "rationale": rationale})


def by_name(client, h):
    return {c["filename"]: c["id"] for c in client.get("/api/cases", headers=h).json()}


def setup_inbox(client):
    cli(demo.reset_demo)
    intake = login(client, "intake1")
    assert len(client.post("/api/intake/poll", headers=intake).json()["created"]) == 3
    return intake, by_name(client, intake)


def test_w1_complete_request_to_decision(client):
    intake, ids = setup_inbox(client)
    a, c = ids["72148_a_complete.pdf"], ids["70551_c_not_met.pdf"]
    nurse1, meddir = login(client, "nurse1"), login(client, "meddir")

    # negatives before review: no login 401, Received case 409
    assert client.post(f"/api/cases/{a}/decision", json={"action": "Approve", "rationale": "x"}).status_code == 401
    assert decide(client, nurse1, a, "Approve").status_code == 409

    # happy path: ops marks ready -> nurse1 approves -> Synced
    cli(demo.mark, a, "ready")
    assert decide(client, intake, a, "Approve").status_code == 403  # wrong role
    r = decide(client, nurse1, a, "Approve", "8 weeks PT documented, radiculopathy")
    assert r.status_code == 200 and r.json()["status"] == "Synced"
    detail = client.get(f"/api/cases/{a}", headers=meddir).json()
    assert detail["sync_detail"].startswith("UM ref UM-")
    assert detail["decisions"][0]["reviewer"] == "Nora Diaz, RN"
    assert client.get("/api/metrics", headers=meddir).json()["cases_reviewed"] == 1

    # alternate: nurse1 pends -> meddir denies
    cli(demo.mark, c, "ready")
    assert decide(client, nurse1, c, "Deny", "no red flags").status_code == 403  # Nurses can't deny
    assert decide(client, nurse1, c, "Pend", "Needs MD review: headache, no red flags").json()["status"] == "Pended"
    assert decide(client, meddir, c, "Deny", "2 weeks of symptoms, no PT or meds trial").json()["status"] == "Synced"
    actors = [(x["actor"], x["details"].get("decision")) for x in
              client.get(f"/api/cases/{c}", headers=meddir).json()["audit"] if x["action"] == "decision"]
    assert actors == [("nurse1", "Pended"), ("meddir", "Denied")]


def test_w2_incomplete_docs_arrive_then_decision(client):
    intake, ids = setup_inbox(client)
    b = ids["73721_b_missing_pt.pdf"]
    nurse1, nurse2 = login(client, "nurse1"), login(client, "nurse2")

    cli(demo.mark, b, "incomplete", "PT notes missing")
    detail = client.get(f"/api/cases/{b}", headers=nurse1).json()
    assert detail["status"] == "Incomplete" and detail["allowed_actions"] == []
    assert "provider_request_sent" in [x["action"] for x in detail["audit"]]
    assert client.get("/api/metrics", headers=nurse1).json()["rework_rate"] == pytest.approx(0.333, abs=0.001)
    assert decide(client, nurse1, b, "Approve").status_code == 409  # negative: wrong status

    # alternate: provider doesn't respond -> stuck after 2 days
    s = new_session(); repo.get_case(s, b).status_changed_at = utcnow() - timedelta(days=3); s.commit(); s.close()
    assert [x["id"] for x in client.get("/api/stuck?days=2", headers=nurse1).json()] == [b]

    # happy path: intake adds PT notes -> Received -> ready -> nurse2 approves
    r = client.post(f"/api/cases/{b}/documents", headers=intake,
                    files={"file": ("73721_b_followup_pt_notes.pdf", b"%PDF pt notes", "application/pdf")})
    assert r.json()["status"] == "Received"
    assert client.get(f"/api/cases/{b}/document?index=1", headers=nurse2).content == b"%PDF pt notes"
    cli(demo.mark, b, "ready")
    assert decide(client, intake, b, "Approve").status_code == 403  # negative: wrong role
    assert decide(client, nurse2, b, "Approve", "PT notes show 8 weeks").json()["status"] == "Synced"
    statuses = [x["details"]["to"] for x in client.get(f"/api/cases/{b}", headers=nurse2).json()["audit"]
                if x["action"] == "status_change"]
    assert statuses == ["Incomplete", "Received", "ReadyForReview", "Approved", "Synced"]
