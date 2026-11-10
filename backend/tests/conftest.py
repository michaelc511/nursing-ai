"""Fresh temp DB + storage + inbox for every test. No network, no .env secrets."""
import pytest


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("INBOX_DIR", str(tmp_path / "inbox"))
    monkeypatch.setenv("SAMPLES_DIR", str(tmp_path / "samples"))
    monkeypatch.setenv("DEMO_PASSWORD", "test-pass")
    monkeypatch.setenv("DEMO_MODE", "")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-32-bytes-long")
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    from app.rag import index
    index.set_embedder(index.HashEmbedder())   # offline, no model download in tests
    index.reset_client()
    (tmp_path / "inbox").mkdir()
    (tmp_path / "samples").mkdir()
    from app import db
    db.reset_engine()
    db.init_db()
    yield tmp_path
    db.reset_engine()
    index.reset_client()


@pytest.fixture
def session():
    from app.db import new_session
    s = new_session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def make_case(session):
    from app.models import Case

    def _make(status="Received", **kw):
        c = Case(source="fax", filename="x.pdf", blob_path="x.pdf", status=status, **kw)
        session.add(c)
        session.flush()
        return c
    return _make
