"""Demo login: one user per role, shared DEMO_PASSWORD from env. Production: SSO + RBAC."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, LockedOut, Unauthorized
from app.models import LoginGuard, Reviewer, utcnow
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
MAX_FAILED_LOGINS = 3
LOCKOUT_HOURS = 24
LOCKED_MESSAGE = "Too many wrong passwords. Sign-in from this network is locked for 24 hours."


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


def demo_hint(today=None) -> dict:
    """Prefill + show the shared password on the login screen, only up to DEMO_AUTOFILL_UNTIL (if set)."""
    from datetime import date, datetime, timezone

    from app.errors import NotFound
    if not settings.demo_mode or not settings.demo_autofill or not settings.demo_password:
        raise NotFound("Password auto-fill is off")
    until = settings.demo_autofill_until
    if until:
        today = today or datetime.now(timezone.utc).date()
        try:
            last_day = date.fromisoformat(until)
        except ValueError:
            raise NotFound("Password auto-fill is off")  # bad date: fail closed
        if today > last_day:
            raise NotFound("Password auto-fill is off")
    return {"password": settings.demo_password, "until": until or None}


def _record_failed_login(session: Session, guard: LoginGuard | None, ip: str, username: str) -> None:
    """Counts a wrong password. Commits itself because the failed request is rolled back afterwards."""
    if guard is None:
        guard = LoginGuard(ip=ip, failures=0)
        session.add(guard)
    guard.failures += 1
    locked = guard.failures >= MAX_FAILED_LOGINS
    if locked:
        guard.locked_until = utcnow() + timedelta(hours=LOCKOUT_HOURS)
        audit.log(session, "system", "login_locked", ip=ip, username=username, hours=LOCKOUT_HOURS)
    session.commit()
    if locked:
        raise LockedOut(LOCKED_MESSAGE)


def login(session: Session, username: str, password: str, ip: str = "unknown") -> tuple[str, Reviewer]:
    guard = session.get(LoginGuard, ip)
    if guard is not None and guard.locked_until is not None:
        if guard.locked_until > utcnow():
            raise LockedOut(LOCKED_MESSAGE)
        session.delete(guard)     # the lockout has expired: start counting again
        session.flush()
        guard = None
    r = repo.get_reviewer_by_username(session, username)
    if r is None or not bcrypt.checkpw(password.encode(), r.password_hash.encode()):
        _record_failed_login(session, guard, ip, username)
        raise Unauthorized("Wrong username or password")
    if guard is not None:
        session.delete(guard)
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    token = jwt.encode({"sub": r.username, "role": r.role, "exp": exp}, settings.secret_key,
                       algorithm="HS256")
    audit.log(session, r.username, "login")
    return token, r


def unlock_logins(session: Session, actor: str = "cli") -> int:
    """Clears every lockout and failure count."""
    guards = session.query(LoginGuard).all()
    for guard in guards:
        session.delete(guard)
    audit.log(session, actor, "logins_unlocked", count=len(guards))
    return len(guards)


def user_from_token(session: Session, token: str) -> Reviewer:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise Unauthorized("Invalid or expired token")
    r = repo.get_reviewer_by_username(session, payload.get("sub", ""))
    if r is None:
        raise Unauthorized("Unknown user")
    return r
