"""Blob storage (swappable). Local folder now; S3/Azure later with the same interface."""
import shutil
import uuid
from pathlib import Path

from app.config import settings


class LocalBlobStorage:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or settings.storage_dir)

    def put_file(self, src: Path) -> str:
        """Copy a file in whole; returns the blob path (pointer stored in SQL)."""
        self.root.mkdir(parents=True, exist_ok=True)
        key = f"{uuid.uuid4().hex}_{Path(src).name}"
        shutil.copyfile(src, self.root / key)
        return key

    def put_bytes(self, name: str, data: bytes) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        key = f"{uuid.uuid4().hex}_{Path(name).name}"
        (self.root / key).write_bytes(data)
        return key

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid blob key")
        return p

    def clear(self) -> None:
        if self.root.exists():
            for f in self.root.iterdir():
                if f.name != ".gitkeep":
                    f.unlink() if f.is_file() else shutil.rmtree(f)


def get_blob_storage() -> LocalBlobStorage:
    return LocalBlobStorage()
