"""Shared FastAPI dependencies: DB session (commit per request) and the logged-in reviewer."""
from fastapi import Depends, Header

from app.db import new_session
from app.errors import Unauthorized
from app.services import auth


def get_session():
    s = new_session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def current_user(authorization: str = Header(default=""), session=Depends(get_session)):
    if not authorization.startswith("Bearer "):
        raise Unauthorized("Login required")
    return auth.user_from_token(session, authorization.removeprefix("Bearer "))
