"""Thin REST routes: parse input -> call a service -> return."""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import current_user, get_session
from app.schemas.api import DecisionIn, DecisionOut, LoginIn, LoginOut
from app.services import auth, cases, decision, demo, intake, policy, review

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, session=Depends(get_session)):
    token, r = auth.login(session, body.username, body.password)
    return LoginOut(token=token, username=r.username, full_name=r.full_name, role=r.role)


@router.get("/auth/demo")
def demo_login_hint():
    """DEMO_MODE only: lets the login screen prefill the shared demo password."""
    return auth.demo_hint()


@router.get("/ai/mode")
def ai_mode():
    """Public: lets every screen say whether AI answers are mocked (AI-MK) or real."""
    from app.config import settings
    from app.services import ai_mode as mode_svc
    eng = review.engine()
    return {"mode": "mock" if eng.label == "AI-MK" else "claude", "label": eng.label,
            "demo": settings.demo_mode,  # the ?icons=ai preview + the switch are demo-mode only
            "switchable": settings.demo_mode, "claude_available": mode_svc.claude_available()}


@router.post("/ai/mode")
def set_ai_mode(body: dict, session=Depends(get_session), user=Depends(current_user)):
    from app.services import ai_mode as mode_svc
    return {"mode": mode_svc.set_mode(session, str(body.get("mode", "")), user.username)}


@router.get("/ai/model")
def ai_model(session=Depends(get_session), user=Depends(current_user)):
    """F2: current Claude model + the allowed list (switchable in demo mode)."""
    from app.config import settings
    from app.llm import client as llm
    return {"model": llm.current_model(session), "models": settings.claude_models,
            "fallback": settings.claude_fallback_model, "switchable": settings.demo_mode}


@router.post("/ai/model")
def set_ai_model(body: dict, session=Depends(get_session), user=Depends(current_user)):
    from app.llm import client as llm
    return {"model": llm.set_model(session, str(body.get("model", "")), user.username)}


@router.get("/ai/usage")
def ai_usage(case_id: int | None = None, session=Depends(get_session), user=Depends(current_user)):
    """F6: AI calls, tokens, cost and average latency (all time, or one case)."""
    from app.llm import client as llm
    return llm.totals(session, case_id=case_id)


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


@router.post("/intake/upload")
def upload(file: UploadFile = File(...), auto_review: bool = True, session=Depends(get_session),
           user=Depends(current_user)):
    c = intake.create_case_from_bytes(session, file.filename, file.file.read(), "upload", user.username)
    if auto_review:
        review.review_case(session, c.id, user.username)
    return cases.summary(session, c)


@router.post("/intake/poll")
def poll(auto_review: bool = True, session=Depends(get_session), user=Depends(current_user)):
    """Check inbox. With auto_review (default) this is the same run_all Cowork uses."""
    if auto_review:
        s = review.run_all(session, user.username, trigger=f"web: Check inbox ({user.username})")
        return {"created": s["new"], "summary": s}
    created = [c.id for c in intake.poll_inbox(session, actor=user.username)]
    return {"created": len(created), "summary": None}


@router.post("/review/run")
def run_reviews(session=Depends(get_session), user=Depends(current_user)):
    """'Run AI review (N new)': reviews every Received case."""
    ids = review.review_received(session, user.username)
    s = review.summarize(session, [], ids, trigger=f"web: Run AI review ({user.username})")
    from app.services import audit
    audit.log(session, user.username, "run_all", None, **s)
    return s


@router.post("/cases/{case_id}/review")
def review_one(case_id: int, session=Depends(get_session), user=Depends(current_user)):
    r = review.review_case(session, case_id, user.username)
    return {"tier": r.tier, "status": cases.get_case(session, case_id).status}


@router.get("/runs/last")
def last_run(session=Depends(get_session), user=Depends(current_user)):
    return review.last_run(session)


@router.post("/cases/{case_id}/documents")
def add_documents(case_id: int, file: UploadFile = File(...), session=Depends(get_session),
                  user=Depends(current_user)):
    c = intake.add_documents(session, case_id, file.filename, file.file.read(), user.username)
    review.review_case(session, c.id, user.username)  # new documents -> AI review again
    return cases.summary(session, c)


@router.get("/cases")
def list_cases(status: str | None = None, tier: str | None = None, session=Depends(get_session),
               user=Depends(current_user)):
    return cases.list_cases(session, status, tier)


@router.get("/cases/{case_id}")
def get_case(case_id: int, session=Depends(get_session), user=Depends(current_user)):
    return cases.detail(session, case_id)


@router.get("/cases/{case_id}/document")
def get_document(case_id: int, index: int = Query(0, ge=0), download: bool = False,
                 session=Depends(get_session), user=Depends(current_user)):
    path, filename = cases.document_path(session, case_id, index, actor=user.username if download else None)
    return FileResponse(path, filename=filename, content_disposition_type="attachment" if download else "inline")


@router.post("/cases/{case_id}/decision", response_model=DecisionOut)
def decide(case_id: int, body: DecisionIn, session=Depends(get_session), user=Depends(current_user)):
    d = decision.decide(session, case_id, user, body.action, body.rationale)
    return DecisionOut(case_id=case_id, decision=d.decision, override=d.override,
                       status=cases.get_case(session, case_id).status)


@router.post("/demo/reset")
def reset_demo(session=Depends(get_session), user=Depends(current_user)):
    """DEMO_MODE only (hidden link in the header, with a confirm popup)."""
    return demo.reset_demo(session, actor=user.username)


@router.get("/policies")
def list_policies(user=Depends(current_user)):
    return policy.list_policies()


@router.get("/policies/{cpt}/search")
def policy_search(cpt: str, q: str = Query(..., min_length=2), k: int = Query(4, ge=1, le=10),
                  user=Depends(current_user)):
    return policy.search(q, cpt=cpt, k=k)


@router.get("/policies/{cpt}/chunks")
def policy_chunks(cpt: str, user=Depends(current_user)):
    return policy.chunks(cpt)


@router.get("/policies/{cpt}/document")
def policy_document(cpt: str, download: bool = False, user=Depends(current_user)):
    path, filename = policy.policy_path(cpt)
    return FileResponse(path, filename=filename, media_type="application/pdf",
                        content_disposition_type="attachment" if download else "inline")


@router.get("/metrics")
def metrics(session=Depends(get_session), user=Depends(current_user)):
    return cases.metrics(session)


@router.get("/stuck")
def stuck(days: float = 2, session=Depends(get_session), user=Depends(current_user)):
    return cases.stuck(session, days)
