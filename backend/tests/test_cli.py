from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_reset_demo_refuses_without_yes():
    r = runner.invoke(app, ["reset-demo"])
    assert r.exit_code == 1


def test_reset_demo_yes_then_poll_and_mark(env, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    (env / "samples" / "72148_a_complete.pdf").write_bytes(b"%PDF a")
    assert runner.invoke(app, ["reset-demo", "--yes"]).exit_code == 0
    r = runner.invoke(app, ["poll"])
    assert "1 new case(s)" in r.output
    r = runner.invoke(app, ["mark", "1", "ready"])
    assert "ReadyForReview" in r.output
    r = runner.invoke(app, ["mark", "1", "ready"])  # illegal: already ReadyForReview
    assert r.exit_code == 1
