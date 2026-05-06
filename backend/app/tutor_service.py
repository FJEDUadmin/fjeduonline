from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from .database import Database
from .gemini_client import GeminiClient

MIN_REQUIRED_QUESTIONS = 4
MAX_UNKNOWN_STREAK = 3


@dataclass(frozen=True)
class TutorReplyResult:
    session_id: str
    status: str
    step: int
    judgement: str
    feedback: str
    next_question: str | None
    final_explanation: str | None
    consecutive_unknown_count: int


class TutorService:
    def __init__(self, *, db: Database, gemini: GeminiClient) -> None:
        self.db = db
        self.gemini = gemini

    def start_session(self, *, user_id: int, problem: str, grade: str | None) -> dict:
        first_question = self.gemini.generate_guiding_question(
            problem=problem,
            grade=grade,
            step=1,
            difficulty_level=0,
            previous_question=None,
            student_answer=None,
            evaluation="start",
        )

        session = self.db.create_tutor_session(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            problem=problem,
            grade=grade,
            status="active",
            total_questions_asked=1,
            consecutive_unknown_count=0,
            difficulty_level=0,
            current_question=first_question,
            history_json="[]",
            final_explanation=None,
        )
        return session

    def reply_session(self, *, user_id: int, session_id: str, answer: str) -> TutorReplyResult:
        session = self.db.get_tutor_session(session_id=session_id, user_id=user_id)
        if not session:
            raise ValueError("找不到對應的引導 session")

        if session["status"] != "active":
            raise ValueError("此引導 session 已結束，請重新開始")

        current_question = session["current_question"]
        evaluation = self.gemini.evaluate_answer(
            problem=session["problem"],
            current_question=current_question,
            student_answer=answer,
            grade=session.get("grade"),
        )
        judgement = evaluation["judgement"]
        feedback = evaluation["feedback"]

        history = json.loads(session["history_json"])
        history.append(
            {
                "step": int(session["total_questions_asked"]),
                "question": current_question,
                "answer": answer,
                "judgement": judgement,
                "feedback": feedback,
            }
        )

        unknown_count = int(session["consecutive_unknown_count"])
        unknown_count = unknown_count + 1 if judgement == "dont_know" else 0

        if unknown_count >= MAX_UNKNOWN_STREAK:
            refusal = "你已連續三次回答『不知道』。請先回去想想我剛剛問的引導題，有答案後再回來。"
            self.db.update_tutor_session(
                session_id=session_id,
                user_id=user_id,
                status="refused",
                consecutive_unknown_count=unknown_count,
                history_json=json.dumps(history, ensure_ascii=False),
                current_question="",
                final_explanation=refusal,
            )
            return TutorReplyResult(
                session_id=session_id,
                status="refused",
                step=int(session["total_questions_asked"]),
                judgement=judgement,
                feedback=feedback,
                next_question=None,
                final_explanation=refusal,
                consecutive_unknown_count=unknown_count,
            )

        asked_count = int(session["total_questions_asked"])
        if asked_count >= MIN_REQUIRED_QUESTIONS and judgement != "dont_know":
            final_explanation = self.gemini.generate_final_explanation(
                problem=session["problem"],
                grade=session.get("grade"),
                turns=history,
            )
            self.db.update_tutor_session(
                session_id=session_id,
                user_id=user_id,
                status="completed",
                consecutive_unknown_count=unknown_count,
                history_json=json.dumps(history, ensure_ascii=False),
                current_question="",
                final_explanation=final_explanation,
            )
            return TutorReplyResult(
                session_id=session_id,
                status="completed",
                step=asked_count,
                judgement=judgement,
                feedback=feedback,
                next_question=None,
                final_explanation=final_explanation,
                consecutive_unknown_count=unknown_count,
            )

        current_difficulty = int(session["difficulty_level"])
        next_difficulty = self._next_difficulty(current_difficulty=current_difficulty, judgement=judgement)
        next_step = asked_count + 1

        next_question = self.gemini.generate_guiding_question(
            problem=session["problem"],
            grade=session.get("grade"),
            step=next_step,
            difficulty_level=next_difficulty,
            previous_question=current_question,
            student_answer=answer,
            evaluation=judgement,
        )

        self.db.update_tutor_session(
            session_id=session_id,
            user_id=user_id,
            status="active",
            total_questions_asked=next_step,
            consecutive_unknown_count=unknown_count,
            difficulty_level=next_difficulty,
            history_json=json.dumps(history, ensure_ascii=False),
            current_question=next_question,
        )

        return TutorReplyResult(
            session_id=session_id,
            status="active",
            step=next_step,
            judgement=judgement,
            feedback=feedback,
            next_question=next_question,
            final_explanation=None,
            consecutive_unknown_count=unknown_count,
        )

    @staticmethod
    def _next_difficulty(*, current_difficulty: int, judgement: str) -> int:
        if judgement == "correct":
            return min(2, current_difficulty + 1)
        if judgement == "incorrect":
            return max(-2, current_difficulty - 1)
        return max(-2, current_difficulty - 1)
