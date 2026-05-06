from __future__ import annotations

import tempfile
import unittest

from app.database import Database
from app.tutor_service import TutorService


class FakeGemini:
    def generate_guiding_question(self, *, problem, grade, step, difficulty_level, previous_question, student_answer, evaluation):
        return f"Q{step}-L{difficulty_level}"

    def evaluate_answer(self, *, problem, current_question, student_answer, grade):
        if "不知道" in student_answer:
            return {"judgement": "dont_know", "feedback": "先補基礎"}
        if "對" in student_answer:
            return {"judgement": "correct", "feedback": "很好，升階"}
        return {"judgement": "incorrect", "feedback": "再試一次"}

    def generate_final_explanation(self, *, problem, grade, turns):
        return f"FINAL-{len(turns)}"


class TutorServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = Database(self.db_file.name)
        self.gemini = FakeGemini()
        self.service = TutorService(db=self.db, gemini=self.gemini)
        user = self.db.create_user(
            email="student@example.com",
            name="Student",
            password_hash="x",
            in_company_class=True,
        )
        self.user_id = user["id"]

    def test_requires_at_least_four_rounds_before_final(self) -> None:
        session = self.service.start_session(user_id=self.user_id, problem="題目A", grade="國三")
        session_id = session["id"]

        for index in range(1, 4):
            result = self.service.reply_session(
                user_id=self.user_id,
                session_id=session_id,
                answer="我答對了",
            )
            self.assertEqual(result.status, "active")
            self.assertEqual(result.step, index + 1)

        final_result = self.service.reply_session(
            user_id=self.user_id,
            session_id=session_id,
            answer="我答對了",
        )
        self.assertEqual(final_result.status, "completed")
        self.assertEqual(final_result.final_explanation, "FINAL-4")

    def test_refuse_after_three_consecutive_unknown(self) -> None:
        session = self.service.start_session(user_id=self.user_id, problem="題目B", grade="國三")
        session_id = session["id"]

        self.service.reply_session(user_id=self.user_id, session_id=session_id, answer="我不知道")
        self.service.reply_session(user_id=self.user_id, session_id=session_id, answer="不知道")
        third = self.service.reply_session(user_id=self.user_id, session_id=session_id, answer="我真的不知道")

        self.assertEqual(third.status, "refused")
        self.assertEqual(third.consecutive_unknown_count, 3)
        self.assertIn("連續三次", third.final_explanation)

    def test_correct_up_incorrect_down_difficulty(self) -> None:
        session = self.service.start_session(user_id=self.user_id, problem="題目C", grade="國三")
        session_id = session["id"]

        self.service.reply_session(user_id=self.user_id, session_id=session_id, answer="我答對了")
        row_after_correct = self.db.get_tutor_session(session_id=session_id, user_id=self.user_id)
        self.assertEqual(row_after_correct["difficulty_level"], 1)

        self.service.reply_session(user_id=self.user_id, session_id=session_id, answer="錯")
        row_after_incorrect = self.db.get_tutor_session(session_id=session_id, user_id=self.user_id)
        self.assertEqual(row_after_incorrect["difficulty_level"], 0)


if __name__ == "__main__":
    unittest.main()
