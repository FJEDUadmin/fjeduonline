from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class Entitlement:
    is_active: bool
    plan: str
    reason: str
    expires_at: str | None
    days_left: int | None


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def compute_entitlement(*, in_company_class: bool, trial_started_at: str | None, trial_days: int) -> Entitlement:
    if in_company_class:
        return Entitlement(
            is_active=True,
            plan="company_student_free",
            reason="公司課程學生可免費使用",
            expires_at=None,
            days_left=None,
        )

    if not trial_started_at:
        return Entitlement(
            is_active=False,
            plan="trial",
            reason="找不到試用開始時間",
            expires_at=None,
            days_left=0,
        )

    start_at = _parse_iso(trial_started_at)
    expires_at = start_at + timedelta(days=trial_days)
    now = datetime.now(timezone.utc)
    active = now < expires_at
    seconds_left = (expires_at - now).total_seconds()
    days_left = max(0, math.ceil(seconds_left / 86400))

    return Entitlement(
        is_active=active,
        plan="trial",
        reason="試用中" if active else "試用已到期",
        expires_at=expires_at.isoformat(),
        days_left=days_left,
    )
