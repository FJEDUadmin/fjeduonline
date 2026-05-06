from __future__ import annotations

import sqlite3
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .auth import hash_password, new_session_token, verify_password
from .config import load_settings
from .database import Database
from .entitlements import compute_entitlement
from .gemini_client import GeminiClient, GeminiConfig, GeminiError
from .schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    SolveRequest,
    SolveResponse,
    EntitlementResponse,
    UserResponse,
)

settings = load_settings()
db = Database(settings.database_path)
gemini = GeminiClient(
    GeminiConfig(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        allow_mock=settings.allow_mock_gemini,
    )
)

app = FastAPI(title="AI Tutor API", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        in_company_class=bool(user["in_company_class"]),
    )


def entitlement_for_user(user: dict) -> EntitlementResponse:
    ent = compute_entitlement(
        in_company_class=bool(user["in_company_class"]),
        trial_started_at=user.get("trial_started_at"),
        trial_days=settings.trial_days,
    )
    return EntitlementResponse(
        is_active=ent.is_active,
        plan=ent.plan,
        reason=ent.reason,
        expires_at=ent.expires_at,
        days_left=ent.days_left,
    )


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Bearer token")

    token = authorization.split(" ", 1)[1].strip()
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="無效的登入狀態")
    return user


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def web_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"page_title": "飛翔少年 AI 助教"},
    )


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> AuthResponse:
    existing = db.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email 已被註冊")

    try:
        user = db.create_user(
            email=payload.email,
            name=payload.name.strip(),
            password_hash=hash_password(payload.password),
            in_company_class=payload.in_company_class,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email 已被註冊") from exc

    token = new_session_token()
    db.create_session(token=token, user_id=user["id"])

    return AuthResponse(token=token, user=to_user_response(user), entitlement=entitlement_for_user(user))


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    user = db.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = new_session_token()
    db.create_session(token=token, user_id=user["id"])

    return AuthResponse(token=token, user=to_user_response(user), entitlement=entitlement_for_user(user))


@app.get("/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    return {"user": to_user_response(current_user), "entitlement": entitlement_for_user(current_user)}


@app.post("/solve", response_model=SolveResponse)
def solve(payload: SolveRequest, current_user: dict = Depends(get_current_user)) -> SolveResponse:
    entitlement = entitlement_for_user(current_user)
    if not entitlement.is_active:
        raise HTTPException(status_code=403, detail=f"目前無可用方案：{entitlement.reason}")

    try:
        answer = gemini.solve(question=payload.question, grade=payload.grade)
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SolveResponse(answer=answer, entitlement=entitlement)
