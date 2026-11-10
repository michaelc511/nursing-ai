"""The AI review contract (CLAUDE.md: 'that schema is the contract between AI and code').

The mock engine (AI-MK) and the Claude engine (Phase 3) must both return exactly this shape.
"""
from typing import Literal

from pydantic import BaseModel, Field


class Fields(BaseModel):
    member_name: str | None = None
    member_id: str | None = None
    dob: str | None = None
    provider_name: str | None = None
    provider_npi: str | None = None
    service: str | None = None
    cpt: str | None = None
    icd10: str | None = None
    diagnosis: str | None = None
    urgency: Literal["Standard", "Expedited"] | None = None


class Evidence(BaseModel):
    quote: str = Field(min_length=1)
    doc: int = Field(0, ge=0, description="0 = original request, 1.. = added documents")
    page: int = Field(ge=1)
    verified: bool | None = None  # set by code, not by the AI


class PolicyEvidence(BaseModel):
    quote: str = Field(min_length=1)
    page: int = Field(ge=1)
    verified: bool | None = None


class Criterion(BaseModel):
    criterion: str
    result: Literal["met", "not_met", "unclear"]
    request_evidence: list[Evidence] = []
    policy_evidence: PolicyEvidence | None = None


class DocumentFound(BaseModel):
    name: str
    doc: int = 0
    page: int = 1


class Missing(BaseModel):
    item: str
    why: str
    policy_page: int | None = None


class Retrieved(BaseModel):
    page: int
    text: str


class ReviewResult(BaseModel):
    fields: Fields
    documents_found: list[DocumentFound] = []
    missing: list[Missing] = []
    complete: bool
    retrieved_criteria: list[Retrieved] = []
    criteria: list[Criterion] = []
    tier: Literal["likely_approve", "needs_review", "likely_deny"]
    summary: str
    draft_provider_request: str | None = None
    warnings: list[str] = []  # set by code (cross-checks)
