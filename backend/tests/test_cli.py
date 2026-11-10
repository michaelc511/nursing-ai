from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_reset_demo_refuses_without_yes():
    r = runner.invoke(app, ["reset-demo"])
    assert r.exit_code == 1


def test_reset_demo_yes_then_poll_and_mark(env, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    (env / "samples" / "72148_a_complete.pdf").write_bytes(b"%PDF a")
    r = runner.invoke(app, ["reset-demo", "--yes"])
    assert r.exit_code == 0 and "1 case(s) loaded and reviewed (AI-MK)" in r.output   # reset fills the queue
    assert "0 new case(s)" in runner.invoke(app, ["poll"]).output
    assert "ReadyForReview" in runner.invoke(app, ["list"]).output
    assert runner.invoke(app, ["mark", "1", "ready"]).exit_code == 1  # illegal: already ReadyForReview
