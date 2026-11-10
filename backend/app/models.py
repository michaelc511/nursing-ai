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
