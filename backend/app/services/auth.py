"""Demo login: one user per role, shared DEMO_PASSWORD from env. Production: SSO + RBAC."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, Unauthorized
from app.models import Reviewer
from app.repositories import cases as repo
from app.services import audit

NURSE, MEDICAL_DIRECTOR, INTAKE = "nurse", "medical_director", "intake"
DEMO_USERS = [
    ("nurse1", "Nora Diaz, RN", NURSE),
    ("nurse2", "Sam Patel, RN", NURSE),
    ("meddir", "Dr. Alex Kim, MD", MEDICAL_DIRECTOR),
    ("intake1", "Riley Chen, Intake Coordinator", INTAKE),
]
TOKEN_HOURS = 12


def seed_reviewers(session: Session) -> int:
    """Create the demo reviewers if missing (re-runnable). Needs DEMO_PASSWORD."""
    if not settings.demo_password:
        raise AppError("DEMO_PASSWORD is not set in .env")
    pw_hash = bcrypt.hashpw(settings.demo_password.encode(), bcrypt.gensalt()).decode()
    created = 0
    for username, full_name, role in DEMO_USERS:
        r = repo.get_reviewer_by_username(session, username)
        if r is None:
            repo.add(session, Reviewer(username=username, full_name=full_name, role=role,
                                       password_hash=pw_hash))
            created += 1
        else:
            r.password_hash = pw_hash  # keep in sync with the current DEMO_PASSWORD
    return created


def demo_hint() -> dict:
    if not settings.demo_mode or not settings.demo_autofill or not settings.demo_password:
        from app.errors import NotFound
        raise NotFound("Password auto-fill is off")
    return {"password": settings.demo_password}


def login(session: Session, username: str, password: str) -> tuple[str, Reviewer]:
    r = repo.get_reviewer_by_username(session, username)
    if r is None or not bcrypt.checkpw(password.encode(), r.password_hash.encode()):
        raise Unauthorized("Wrong username or password")
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    token = jwt.encode({"sub": r.username, "role": r.role, "exp": exp}, settings.secret_key,
                       algorithm="HS256")
    audit.log(session, r.username, "login")
    return token, r


def user_from_token(session: Session, token: str) -> Reviewer:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise Unauthorized("Invalid or expired token")
    r = repo.get_reviewer_by_username(session, payload.get("sub", ""))
    if r is None:
        raise Unauthorized("Unknown user")
    return r
