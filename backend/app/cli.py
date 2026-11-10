"""Thin Typer CLI over services/. Run from backend/: python -m app.cli <command>."""
import json
from contextlib import contextmanager

import typer

from app.db import init_db, new_session
from app.errors import AppError
from app.services import auth, cases, demo, intake, review

app = typer.Typer(help="NurseOps Now CLI (prior authorization)", no_args_is_help=True)


@contextmanager
def session_scope():
    init_db()
    s = new_session()
    try:
        yield s
        s.commit()
    except AppError as e:
        s.rollback()
        typer.secho(f"Error: {e.detail}", fg="red", err=True)
        raise typer.Exit(1)
    finally:
        s.close()


@app.command("init-db")
def init_db_cmd():
    """Create tables and seed the demo reviewers (needs DEMO_PASSWORD)."""
    with session_scope() as s:
        n = auth.seed_reviewers(s)
    typer.echo(f"Database ready; {n} reviewer(s) created")


@app.command()
def poll():
    """Intake: scan ./inbox and create a case per file."""
    with session_scope() as s:
        created = intake.poll_inbox(s, actor="cli")
        typer.echo(f"{len(created)} new case(s): {[c.id for c in created]}")


@app.command("review")
def review_cmd(case_id: int):
    """AI review one case (AI_MODE=mock -> AI-MK)."""
    with session_scope() as s:
        r = review.review_case(s, case_id, actor="cli")
        typer.echo(f"Case {case_id}: {r.tier} ({r.result.get('engine')}) -> {cases.get_case(s, case_id).status}")


@app.command("run-all")
def run_all_cmd():
    """Poll the inbox + AI review all new cases (what Cowork runs)."""
    with session_scope() as s:
        typer.echo(json.dumps(review.run_all(s, actor="cli", trigger="cli: run-all"), indent=2))


@app.command()
def status():
    """Case counts by status + metrics."""
    with session_scope() as s:
        typer.echo(json.dumps(cases.metrics(s), indent=2))


@app.command()
def stuck(days: float = typer.Option(2, help="days in the same status")):
    """Cases stuck in an open status for more than N days."""
    with session_scope() as s:
        rows = cases.stuck(s, days)
        for r in rows:
            typer.echo(f"#{r['id']} {r['status']} {r['days_in_status']}d {r['filename']}")
        typer.echo(f"{len(rows)} stuck case(s) (> {days} days)")


@app.command("list")
def list_cmd(status: str = typer.Option(None, help="filter by status")):
    """List cases."""
    with session_scope() as s:
        for r in cases.list_cases(s, status):
            typer.echo(f"#{r['id']} {r['status']:<15} {r['tier'] or '-':<15} {r['filename']}")


@app.command()
def mark(case_id: int, target: str = typer.Argument(..., help="ready | incomplete"),
         note: str = typer.Option("", help="reason")):
    """TEST-ONLY until Phase 3 AI review: move a Received case to ReadyForReview or Incomplete."""
    with session_scope() as s:
        typer.echo(f"Case {case_id} -> {demo.mark(s, case_id, target, note)}")


@app.command("reset-demo")
def reset_demo(yes: bool = typer.Option(False, "--yes", help="confirm wiping all cases")):
    """Wipe all cases/storage/inbox and reload the sample faxes (needs DEMO_MODE=true)."""
    if not yes:
        typer.secho("Refusing without --yes (this deletes every case)", fg="red", err=True)
        raise typer.Exit(1)
    with session_scope() as s:
        r = demo.reset_demo(s)
    s = r["summary"]
    typer.echo(f"Demo reset: {s['new']} case(s) loaded and reviewed ({s['engine']}), "
               f"{len(s['incomplete'])} incomplete.")



@app.command("index-policies")
def index_policies_cmd():
    """(Re)embed the policy PDFs into Chroma (clause-aware chunks + metadata)."""
    from app.services import policy
    r = policy.index_policies()
    typer.echo(f"Embedder: {r['embedder']}")
    for p in r["policies"]:
        flag = f", FLAGGED (kept out): {p['flagged']}" if p["flagged"] else ""
        typer.echo(f"  CPT {p['cpt']} v{p['version']}: {p['chunks']} chunks{flag}")
    typer.echo(f"Total chunks: {r['total_chunks']}")


@app.command("search-policies")
def search_policies_cmd(query: str, cpt: str = typer.Option(None, help="search only this CPT's policy"),
                        k: int = typer.Option(3, help="number of chunks")):
    """Retrieval only (no LLM): top policy chunks for a question."""
    from app.services import policy
    for i, c in enumerate(policy.search(query, cpt=cpt, k=k), 1):
        typer.echo(f"\n#{i} score {c['score']}  {c['policy_number']} v{c['version']} {c['label']} "
                   f"{c['section_title']} (page {c['page']})\n{c['quote']}")


if __name__ == "__main__":
    app()
