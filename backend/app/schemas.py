from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    in_company_class: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class SolveRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    grade: str | None = Field(default=None, max_length=50)


class TutorStartRequest(BaseModel):
    problem: str = Field(min_length=3, max_length=5000)
    grade: str | None = Field(default=None, max_length=50)


class TutorReplyRequest(BaseModel):
    session_id: str = Field(min_length=10, max_length=120)
    answer: str = Field(min_length=1, max_length=5000)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    in_company_class: bool


class EntitlementResponse(BaseModel):
    is_active: bool
    plan: str
    reason: str
    expires_at: str | None
    days_left: int | None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    entitlement: EntitlementResponse


class SolveResponse(BaseModel):
    answer: str
    entitlement: EntitlementResponse


class TutorStartResponse(BaseModel):
    session_id: str
    status: Literal["active"]
    step: int
    min_required_steps: int
    question: str
    entitlement: EntitlementResponse


class TutorReplyResponse(BaseModel):
    session_id: str
    status: Literal["active", "completed", "refused"]
    step: int
    judgement: Literal["correct", "incorrect", "dont_know"]
    feedback: str
    next_question: str | None
    final_explanation: str | None
    consecutive_unknown_count: int
    entitlement: EntitlementResponse
