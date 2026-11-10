"""FastAPI app: REST adapter over services/ (+ serves the built React UI if present)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import ROOT
from app.db import init_db
from app.errors import AppError

from app.mcp_server import mcp


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app import pii
    from app.services import observability
    init_db()
    pii.install_log_filter()                      # S5: no PII in application logs
    observability.configure_langsmith()           # F9: LangSmith only if configured, content hidden
    mcp._session_manager = None                   # fresh session manager per app start (tests restart it)
    mcp_guard.inner = mcp.streamable_http_app()
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="NurseOps Now API", version="0.4.0", lifespan=lifespan)
app.include_router(router)


class BearerGuard:
    """Dev Phase 2: simple bearer-token auth for /mcp (MCP_TOKEN in .env). No token set -> MCP off."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            import hmac
            import os
            token = os.environ.get("MCP_TOKEN", "")
            got = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
            if not token or not hmac.compare_digest(got, f"Bearer {token}"):
                res = JSONResponse(status_code=503 if not token else 401,
                                   content={"detail": "MCP disabled (set MCP_TOKEN)" if not token else "Bad MCP token"})
                return await res(scope, receive, send)
        return await self.inner(scope, receive, send)


mcp_guard = BearerGuard(None)
app.mount("/mcp", mcp_guard)


@app.exception_handler(AppError)
def app_error(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health():
    return {"status": "ok"}


DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        # index.html must never be cached, or browsers keep showing an old build
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
