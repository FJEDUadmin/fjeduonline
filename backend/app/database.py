from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    in_company_class INTEGER NOT NULL DEFAULT 0,
                    trial_started_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tutor_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    problem TEXT NOT NULL,
                    grade TEXT,
                    status TEXT NOT NULL,
                    total_questions_asked INTEGER NOT NULL,
                    consecutive_unknown_count INTEGER NOT NULL,
                    difficulty_level INTEGER NOT NULL,
                    current_question TEXT NOT NULL,
                    history_json TEXT NOT NULL,
                    final_explanation TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.commit()

    def create_user(
        self,
        *,
        email: str,
        name: str,
        password_hash: str,
        in_company_class: bool,
    ) -> dict[str, Any]:
        now = utcnow_iso()
        trial_started_at = None if in_company_class else now
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    email, name, password_hash, in_company_class, trial_started_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (email, name, password_hash, int(in_company_class), trial_started_at, now),
            )
            user_id = cursor.lastrowid
            conn.commit()
        return self.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_session(self, *, token: str, user_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, utcnow_iso()),
            )
            conn.commit()

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT u.*
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
        return dict(row) if row else None

    def create_tutor_session(
        self,
        *,
        session_id: str,
        user_id: int,
        problem: str,
        grade: str | None,
        status: str,
        total_questions_asked: int,
        consecutive_unknown_count: int,
        difficulty_level: int,
        current_question: str,
        history_json: str,
        final_explanation: str | None,
    ) -> dict[str, Any]:
        now = utcnow_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tutor_sessions (
                    id, user_id, problem, grade, status, total_questions_asked,
                    consecutive_unknown_count, difficulty_level, current_question,
                    history_json, final_explanation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    problem,
                    grade,
                    status,
                    total_questions_asked,
                    consecutive_unknown_count,
                    difficulty_level,
                    current_question,
                    history_json,
                    final_explanation,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_tutor_session(session_id=session_id, user_id=user_id)

    def get_tutor_session(self, *, session_id: str, user_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM tutor_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        return dict(row) if row else None

    def update_tutor_session(self, *, session_id: str, user_id: int, **fields: Any) -> None:
        if not fields:
            return

        fields["updated_at"] = utcnow_iso()
        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values()) + [session_id, user_id]

        with self.connect() as conn:
            conn.execute(
                f"UPDATE tutor_sessions SET {assignments} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
