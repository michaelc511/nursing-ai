import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.db import new_session
    from app.main import app
    from app.services import auth
    s = new_session()
    auth.seed_reviewers(s)
    s.commit()
    s.close()
    with TestClient(app) as c:
        yield c


def login(client, user="nurse1"):
    r = client.post("/api/auth/login", json={"username": user, "password": "test-pass"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_required(client):
    assert client.get("/api/cases").status_code == 401


def test_bad_login(client):
    assert client.post("/api/auth/login", json={"username": "nurse1", "password": "x"}).status_code == 401


@pytest.mark.parametrize("name,data", [("fake.pdf", b"not a pdf"), ("empty.pdf", b""), ("fake.png", b"%PDF-1.4"),
                                       ("fake.jpg", b"plain text"), ("fake.tif", b"plain text")])
def test_upload_rejects_file_that_is_not_its_type(client, name, data):
    h = login(client)
    r = client.post("/api/intake/upload", headers=h, files={"file": (name, data, "application/octet-stream")})
    assert r.status_code == 400 and "not really" in r.json()["detail"]
    assert client.get("/api/cases", headers=h).json() == []


def test_add_documents_rejects_fake_file_and_keeps_status(client):
    h = login(client)
    cid = client.post("/api/intake/upload?auto_review=false", headers=h,
                      files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")}).json()["id"]
    from app.db import new_session
    from app.services import demo
    s = new_session(); demo.mark(s, cid, "incomplete"); s.commit(); s.close()
    r = client.post(f"/api/cases/{cid}/documents", headers=h, files={"file": ("pt.pdf", b"junk", "application/pdf")})
    assert r.status_code == 400
    assert client.get(f"/api/cases/{cid}", headers=h).json()["status"] == "Incomplete"


def test_inbox_file_that_is_damaged_still_reaches_a_human(client, env):
    h = login(client)
    (env / "inbox" / "bad.pdf").write_bytes(b"junk")
    (env / "inbox" / "good.pdf").write_bytes(b"%PDF-1.4 ok")
    r = client.post("/api/intake/poll?auto_review=false", headers=h)
    assert r.status_code == 200 and r.json()["created"] == 2
    assert not (env / "inbox" / "bad.pdf").exists()


def test_upload_view_and_decide_flow(client):
    h = login(client)
    r = client.post("/api/intake/upload?auto_review=false", headers=h,
                    files={"file": ("72148_a.pdf", b"%PDF-1.4 demo", "application/pdf")})
    cid = r.json()["id"]
    assert r.json()["status"] == "Received"
    assert client.get(f"/api/cases/{cid}/document", headers=h).content == b"%PDF-1.4 demo"
    # can't decide before review
    assert client.post(f"/api/cases/{cid}/decision", headers=h,
                       json={"action": "Approve", "rationale": "ok"}).status_code == 409
    from app.db import new_session
    from app.services import demo
    s = new_session(); demo.mark(s, cid, "ready"); s.commit(); s.close()
    r = client.post(f"/api/cases/{cid}/decision", headers=h, json={"action": "Approve", "rationale": "Meets criteria"})
    assert r.status_code == 200 and r.json()["status"] == "Synced"
    detail = client.get(f"/api/cases/{cid}", headers=h).json()
    assert detail["decisions"][0]["reviewer"] == "Nora Diaz, RN"
    assert [a["action"] for a in detail["audit"]][-1] == "status_change"
    assert client.get("/api/metrics", headers=h).json()["cases_reviewed"] == 1


def test_unknown_case_404(client):
    assert client.get("/api/cases/999", headers=login(client)).status_code == 404


def test_demo_password_hint_only_in_demo_mode(client, monkeypatch):
    assert client.get("/api/auth/demo").status_code == 404
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get("/api/auth/demo").json() == {"password": "test-pass"}


def test_web_reset_demo_mode_only(client, monkeypatch):
    h = login(client)
    client.post("/api/intake/upload", headers=h, files={"file": ("a.pdf", b"%PDF", "application/pdf")})
    assert client.post("/api/demo/reset", headers=h).status_code == 403
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.post("/api/demo/reset", headers=h).status_code == 200
    assert client.get("/api/cases", headers=h).json() == []
    assert client.post("/api/demo/reset").status_code == 401


def test_policy_endpoints(client):
    h = login(client)
    assert client.get("/api/policies").status_code == 401
    assert len(client.get("/api/policies", headers=h).json()) == 3
    r = client.get("/api/policies/73721/document", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and "inline" in r.headers["content-disposition"]
    r = client.get("/api/policies/73721/document?download=true", headers=h)
    assert "attachment" in r.headers["content-disposition"]
    assert client.get("/api/policies/00000/document", headers=h).status_code == 404


def test_request_download_is_audited(client):
    h = login(client)
    cid = client.post("/api/intake/upload", headers=h,
                      files={"file": ("72148_a.pdf", b"%PDF-1.4 x", "application/pdf")}).json()["id"]
    assert client.get(f"/api/cases/{cid}/document", headers=h).status_code == 200      # view: not logged
    r = client.get(f"/api/cases/{cid}/document?download=true", headers=h)
    assert "attachment" in r.headers["content-disposition"] and r.content == b"%PDF-1.4 x"
    actions = [a["action"] for a in client.get(f"/api/cases/{cid}", headers=h).json()["audit"]]
    assert actions.count("document_downloaded") == 1
    assert client.get(f"/api/cases/{cid}/document?download=true").status_code == 401


def test_ai_mode_is_public_and_mock_by_default(client, monkeypatch):
    m = client.get("/api/ai/mode").json()
    assert (m["mode"], m["label"], m["demo"], m["switchable"], m["claude_available"]) == ("mock", "AI-MK", False, False, False)
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get("/api/ai/mode").json()["demo"] is True


def test_ai_mode_switch_rules(client, monkeypatch):
    h = login(client)
    assert client.post("/api/ai/mode", json={"mode": "mock"}).status_code == 401
    assert client.post("/api/ai/mode", headers=h, json={"mode": "mock"}).status_code == 403   # not demo mode
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.post("/api/ai/mode", headers=h, json={"mode": "claude"}).status_code == 400  # Claude not ready
    assert client.post("/api/ai/mode", headers=h, json={"mode": "mock"}).json() == {"mode": "mock"}
    from app.services import review
    review.ClaudeEngine.ready = True
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    try:
        assert client.post("/api/ai/mode", headers=h, json={"mode": "claude"}).json() == {"mode": "claude"}
        assert client.get("/api/ai/mode").json()["label"] == "AI"
    finally:
        review.ClaudeEngine.ready = False
