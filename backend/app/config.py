from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    allow_mock_gemini: bool
    database_path: str
    trial_days: int


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_settings() -> Settings:
    _load_dotenv_if_present()
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip(),
        allow_mock_gemini=_as_bool(os.getenv("ALLOW_MOCK_GEMINI", "true"), default=True),
        database_path=os.getenv("APP_DATABASE_PATH", "./app.db").strip(),
        trial_days=int(os.getenv("TRIAL_DAYS", "30")),
    )
