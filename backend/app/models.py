"""SQLAlchemy models: cases, ai_reviews, decisions, audit_log (CLAUDE.md) + reviewers (Phase 2.5)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Setting(Base):
    """Small runtime settings (e.g. the demo AI mode switch)."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


class Reviewer(Base):
    __tablename__ = "reviewers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))  # nurse | medical_director | intake
    password_hash: Mapped[str] = mapped_column(String(100))


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(30))  # fax | upload | portal
    filename: Mapped[str] = mapped_column(String(255))
    blob_path: Mapped[str] = mapped_column(String(500))  # main document (pointer into blob storage)
    extra_documents: Mapped[list] = mapped_column(JSON, default=list)  # later docs (e.g. PT notes)
    diagnosis: Mapped[str | None] = mapped_column(String(200), nullable=True)  # from the AI review
    cpt: Mapped[str | None] = mapped_column(String(5), nullable=True)  # read from the form (#2a)
    status: Mapped[str] = mapped_column(String(30), default="Received")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sync_status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # pending | synced
    sync_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviews = relationship("AIReview", back_populates="case", order_by="AIReview.id")
    decisions = relationship("Decision", back_populates="case", order_by="Decision.id")


class AIReview(Base):
    __tablename__ = "ai_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    result: Mapped[dict] = mapped_column(JSON)  # validated Claude JSON (Phase 3-4)
    tier: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    case = relationship("Case", back_populates="reviews")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("reviewers.id"))
    decision: Mapped[str] = mapped_column(String(20))  # Approved | Denied | Pended
    rationale: Mapped[str] = mapped_column(Text)
    ai_tier: Mapped[str | None] = mapped_column(String(30), nullable=True)
    override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    case = relationship("Case", back_populates="decisions")
    reviewer = relationship("Reviewer")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(100))  # username, "system", "cli"
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LLMCall(Base):
    """F6: one row per AI call (Claude or AI-MK): tokens, cost, latency. Never stores prompt text."""
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(40))          # review | rewrite | chat | judge ...
    engine: Mapped[str] = mapped_column(String(20))           # AI-MK | AI
    model: Mapped[str] = mapped_column(String(60))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)   # N3: answered from the cache
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | refused | error | fallback
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LLMCache(Base):
    """N3: exact-input cache (same documents + policy version + prompt + model -> same answer)."""
    __tablename__ = "llm_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(60))
    value: Mapped[dict] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Trace(Base):
    """F9: one row per AI run (review graph or AI Assist turn): node timings, tokens, cost. No content."""
    __tablename__ = "traces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))                  # review | assist
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    engine: Mapped[str | None] = mapped_column(String(20), nullable=True)
    steps: Mapped[list] = mapped_column(JSON, default=list)        # [{"node", "ms"}]
    total_ms: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)   # tier, blocked reason ...
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    """N4: staff thumbs up/down on an AI review or an AI Assist answer."""
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))                  # review | assist
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)                   # +1 | -1
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)   # assist only, PII-redacted
    actor: Mapped[str] = mapped_column(String(100))
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
