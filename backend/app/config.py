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
    def ai_mode(self) -> str:
        """mock (AI-MK, prepared answers) | claude (Phase 3)."""
        return (_get("AI_MODE") or "mock").lower()

    @property
    def claude_model(self) -> str:
        """CLAUDE.md: model from env. Default Claude Opus 5.5."""
        return _get("CLAUDE_MODEL") or "claude-opus-5-5"

    @property
    def claude_models(self) -> list[str]:
        """F2: models staff may pick in demo mode (comma list)."""
        raw = _get("CLAUDE_MODELS") or "claude-opus-5-5,claude-sonnet-5-5,claude-haiku-5-5"
        return [m.strip() for m in raw.split(",") if m.strip()]

    @property
    def claude_fallback_model(self) -> str:
        """N3: tried when the main model is overloaded or down. Empty = no model fallback."""
        return _get("CLAUDE_FALLBACK_MODEL", "claude-sonnet-5-5")

    @property
    def claude_effort(self) -> str:
        return _get("CLAUDE_EFFORT") or "high"

    @property
    def llm_cache(self) -> bool:
        return _get("LLM_CACHE", "true").lower() in {"1", "true", "yes"}

    @property
    def review_pipeline(self) -> str:
        """graph (LangGraph, Phase 5) | linear (F12.1 frozen baseline)."""
        return (_get("REVIEW_PIPELINE") or "graph").lower()

    @property
    def max_case_cost_usd(self) -> float:
        """Per-case AI cost cap: no retries once a case has cost this much."""
        return float(_get("MAX_CASE_COST_USD") or 0.50)

    @property
    def assist_db(self) -> Path:
        """AI Assist chat memory (LangGraph SqliteSaver checkpoints)."""
        return Path(_get("ASSIST_DB") or BACKEND / "data" / "assist_memory.db")

    @property
    def assist_turns(self) -> int:
        return int(_get("ASSIST_TURNS") or 10)

    @property
    def hybrid(self) -> bool:
        """F18: BM25 + vector with Reciprocal Rank Fusion."""
        return _get("HYBRID_SEARCH", "true").lower() in {"1", "true", "yes"}

    @property
    def rerank(self) -> bool:
        """F10: cross-encoder re-ranking of the top 10."""
        return _get("RERANK", "true").lower() in {"1", "true", "yes"}

    @property
    def rerank_model(self) -> str:
        return _get("RERANK_MODEL") or "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @property
    def query_rewrite(self) -> bool:
        """S8: Claude rewrites the search query in policy wording (Claude mode only)."""
        return _get("QUERY_REWRITE", "true").lower() in {"1", "true", "yes"}

    @property
    def ai_calls_per_minute(self) -> int:
        """F21: AI requests per user per minute (review runs, AI Assist)."""
        return int(_get("AI_CALLS_PER_MINUTE") or 20)

    @property
    def daily_cost_cap_usd(self) -> float:
        """F21: AI spend cap per day (UTC) for the whole app; then AI pauses and people review."""
        return float(_get("DAILY_COST_CAP_USD") or 10)

    @property
    def chroma_dir(self) -> Path:
        """Policy RAG index (Chroma). Rebuild with: python -m app.cli index-policies."""
        return Path(_get("CHROMA_DIR") or BACKEND / "data" / "chroma")

    @property
    def embed_model(self) -> str:
        return _get("EMBED_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"

    @property
    def secret_key(self) -> str:
        return _get("SECRET_KEY") or "dev-only-secret-change-me-in-env-0123456789"


settings = Settings()
