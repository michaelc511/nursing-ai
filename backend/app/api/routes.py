"""Thin REST routes: parse input -> call a service -> return."""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import current_user, get_session
from app.schemas.api import DecisionIn, DecisionOut, LoginIn, LoginOut
from app.services import auth, cases, decision, demo, intake, policy

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, session=Depends(get_session)):
    token, r = auth.login(session, body.username, body.password)
    return LoginOut(token=token, username=r.username, full_name=r.full_name, role=r.role)


@router.get("/auth/demo")
def demo_login_hint():
    """DEMO_MODE only: lets the login screen prefill the shared demo password."""
    return auth.demo_hint()


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


@router.post("/intake/upload")
def upload(file: UploadFile = File(...), session=Depends(get_session), user=Depends(current_user)):
    c = intake.create_case_from_bytes(session, file.filename, file.file.read(), "upload", user.username)
    return cases.summary(session, c)


@router.post("/intake/poll")
def poll(session=Depends(get_session), user=Depends(current_user)):
    return {"created": [c.id for c in intake.poll_inbox(session, actor=user.username)]}


@router.post("/cases/{case_id}/documents")
def add_documents(case_id: int, file: UploadFile = File(...), session=Depends(get_session),
                  user=Depends(current_user)):
    c = intake.add_documents(session, case_id, file.filename, file.file.read(), user.username)
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


@router.post("/demo/cases/{case_id}/check")
def simulate_check(case_id: int, result: str = Query(..., pattern="^(ready|incomplete)$"),
                   session=Depends(get_session), user=Depends(current_user)):
    return {"status": demo.simulate_check(session, case_id, result, user.username)}


@router.post("/demo/reset")
def reset_demo(session=Depends(get_session), user=Depends(current_user)):
    """DEMO_MODE only (hidden link in the header, with a confirm popup)."""
    return demo.reset_demo(session, actor=user.username)


@router.get("/policies")
def list_policies(user=Depends(current_user)):
    return policy.list_policies()


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
