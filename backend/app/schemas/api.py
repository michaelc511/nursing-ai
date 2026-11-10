"""Request/response models for the REST API."""
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    username: str
    full_name: str
    role: str


class DecisionIn(BaseModel):
    action: str = Field(description="Approve | Deny | Pend")
    rationale: str = Field(min_length=1)


class DecisionOut(BaseModel):
    case_id: int
    decision: str
    override: bool
    status: str
