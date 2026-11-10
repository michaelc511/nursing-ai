"""Layer 1: intake. Store the file whole in blob storage + a SQL row (status Received)."""
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, NotFound
from app.models import Case
from app.repositories import cases as repo
from app.repositories.blob import get_blob_storage
from app.services import audit, state

ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
_TIFF = (b"II*\x00", b"MM\x00*")
SIGNATURES = {".pdf": (b"%PDF",), ".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",),
              ".jpeg": (b"\xff\xd8\xff",), ".tif": _TIFF, ".tiff": _TIFF}
CHANNELS = {"fax", "portal", "upload"}


def _sample_info(filename: str) -> tuple[str, str | None]:
    """Demo: the sample manifest gives each sample's channel + diagnosis. Unknown files: fax, no diagnosis."""
    import json
    try:
        entry = json.loads((settings.samples_dir / "manifest.json").read_text()).get(filename, {})
    except (OSError, ValueError):
        entry = {}
    if isinstance(entry, str):
        entry = {"channel": entry}
    channel = entry.get("channel", "fax")
    return (channel if channel in CHANNELS else "fax"), entry.get("diagnosis")


def _check_type(name: str) -> None:
    if Path(name).suffix.lower() not in ALLOWED_TYPES:
        raise AppError(f"Unsupported file type: {name} (allowed: {', '.join(sorted(ALLOWED_TYPES))})")


def _content_matches(name: str, data: bytes) -> bool:
    """The bytes must really be the type the extension claims (a renamed file never reaches a nurse)."""
    return data.startswith(SIGNATURES.get(Path(name).suffix.lower(), ()))


def _check_file(name: str, data: bytes) -> None:
    _check_type(name)
    if not _content_matches(name, data):
        raise AppError(f"{name} is empty, damaged or not really a {Path(name).suffix.lower()} file")


def _arrival_order(f: Path) -> tuple[int, str]:
    """Demo samples arrive in manifest order (A, B, C); other files after them, by name."""
    import json
    try:
        keys = [k for k in json.loads((settings.samples_dir / "manifest.json").read_text()) if not k.startswith("_")]
    except (OSError, ValueError):
        keys = []
    return (keys.index(f.name) if f.name in keys else len(keys), f.name)


def create_case_from_bytes(session: Session, filename: str, data: bytes, source: str = "upload",
                           actor: str = "system") -> Case:
    _check_type(filename)
    key = get_blob_storage().put_bytes(filename, data)
    case = repo.add(session, Case(source=source, filename=Path(filename).name, blob_path=key,
                                  status=state.RECEIVED))
    audit.log(session, actor, "intake", case.id, source=source, filename=case.filename)
    return case


def create_case_from_upload(session: Session, filename: str, data: bytes, actor: str = "system") -> Case:
    """Web upload: the sender is present, so a bad file is refused. Inbox files (faxes) still go to a human."""
    _check_file(filename, data)
    return create_case_from_bytes(session, filename, data, "upload", actor)


def poll_inbox(session: Session, actor: str = "system") -> list[Case]:
    """Scan the inbox, create one case per supported file, remove the file from the inbox."""
    inbox = settings.inbox_dir
    created = []
    if not inbox.exists():
        return created
    for f in sorted(inbox.iterdir(), key=_arrival_order):
        if not f.is_file() or f.suffix.lower() not in ALLOWED_TYPES:
            continue
        channel, _ = _sample_info(f.name)
        case = create_case_from_bytes(session, f.name, f.read_bytes(), source=channel, actor=actor)
        f.unlink()
        created.append(case)
    return created


def add_documents(session: Session, case_id: int, filename: str, data: bytes,
                  actor: str = "system") -> Case:
    """New docs for an Incomplete case: store them and move Incomplete -> Received."""
    _check_file(filename, data)
    case = repo.get_case(session, case_id)
    if case is None:
        raise NotFound(f"Case {case_id} not found")
    key = get_blob_storage().put_bytes(filename, data)
    case.extra_documents = [*(case.extra_documents or []), {"filename": Path(filename).name, "blob_path": key}]
    audit.log(session, actor, "documents_added", case.id, filename=Path(filename).name, blob_path=key)
    state.transition(session, case, state.RECEIVED, actor, reason="new documents arrived")
    return case
