"""Settings from env vars (.env at the repo root). Never hard-code secrets."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings:
    @property
    def database_url(self) -> str:
        return _get("DATABASE_URL") or f"sqlite:///{BACKEND / 'data' / 'app.db'}"

    @property
    def storage_dir(self) -> Path:
        return Path(_get("STORAGE_DIR") or ROOT / "storage")

    @property
    def inbox_dir(self) -> Path:
        return Path(_get("INBOX_DIR") or ROOT / "inbox")

    @property
    def samples_dir(self) -> Path:
        return Path(_get("SAMPLES_DIR") or ROOT / "data" / "samples")

    @property
    def demo_password(self) -> str:
        return _get("DEMO_PASSWORD")

    @property
    def demo_mode(self) -> bool:
        return _get("DEMO_MODE").lower() in {"1", "true", "yes"}

    @property
    def secret_key(self) -> str:
        return _get("SECRET_KEY") or "dev-only-secret-change-me-in-env-0123456789"


settings = Settings()
