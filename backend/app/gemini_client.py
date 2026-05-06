from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib import error, parse, request


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str
    allow_mock: bool


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, config: GeminiConfig) -> None:
        self.config = config

    def solve(self, *, question: str, grade: str | None = None) -> str:
        if not self.config.api_key:
            if self.config.allow_mock:
                return (
                    "[Mock 回應] 目前未設定 GEMINI_API_KEY。\n"
                    "你可以先用這個版本驗證流程，設定金鑰後就會改成 Gemini 真實解題。\n\n"
                    f"題目：{question[:300]}"
                )
            raise GeminiError("GEMINI_API_KEY 未設定")

        grade_hint = f"學生程度：{grade}\n" if grade else ""
        prompt = (
            "你是一位 AI 解題助教，請用繁體中文回答。\n"
            "請先列出解題重點，再給步驟，最後補充常見錯誤。\n"
            "若題目資訊不足，先說明缺什麼資訊。\n\n"
            f"{grade_hint}"
            f"題目：\n{question}"
        )
        return self._generate_text(prompt)

    def evaluate_answer(
        self,
        *,
        problem: str,
        current_question: str,
        student_answer: str,
        grade: str | None,
    ) -> dict[str, str]:
        if not self.config.api_key:
            if self.config.allow_mock:
                return self._mock_evaluation(student_answer)
            raise GeminiError("GEMINI_API_KEY 未設定")

        grade_hint = f"學生程度：{grade}\n" if grade else ""
        prompt = (
            "你是教學評估助教。請判斷學生回答的理解程度。\n"
            "只能回傳 JSON，不要加任何 markdown。\n"
            "JSON 格式：{\"judgement\":\"correct|incorrect|dont_know\",\"feedback\":\"...\"}\n"
            "判斷規則：\n"
            "- correct: 核心概念正確，允許小瑕疵\n"
            "- incorrect: 有嘗試但關鍵錯誤\n"
            "- dont_know: 明確表達不知道/不會/無法作答\n\n"
            f"{grade_hint}"
            f"原題目：{problem}\n"
            f"目前引導問題：{current_question}\n"
            f"學生回答：{student_answer}"
        )
        raw = self._generate_text(prompt)
        parsed = self._extract_json(raw)

        judgement = str(parsed.get("judgement", "incorrect")).strip().lower()
        if judgement not in {"correct", "incorrect", "dont_know"}:
            judgement = "incorrect"

        feedback = str(parsed.get("feedback", "我看到你的想法了，我們再試一步。")).strip()
        if not feedback:
            feedback = "我看到你的想法了，我們再試一步。"

        return {"judgement": judgement, "feedback": feedback}

    def generate_guiding_question(
        self,
        *,
        problem: str,
        grade: str | None,
        step: int,
        difficulty_level: int,
        previous_question: str | None,
        student_answer: str | None,
        evaluation: str,
    ) -> str:
        if not self.config.api_key:
            if self.config.allow_mock:
                return self._mock_guiding_question(
                    problem=problem,
                    step=step,
                    difficulty_level=difficulty_level,
                    evaluation=evaluation,
                )
            raise GeminiError("GEMINI_API_KEY 未設定")

        grade_hint = f"學生程度：{grade}\n" if grade else ""
        difficulty_hint = {
            -2: "大幅降階，先確認最基礎定義",
            -1: "降階，提供更具體提示",
            0: "維持目前難度",
            1: "升階，增加一點延伸推理",
            2: "進階，加入跨概念挑戰",
        }.get(difficulty_level, "維持目前難度")

        prompt = (
            "你是引導式思考 AI 助教。請只出一題引導問題，不要直接給答案。\n"
            "限制：\n"
            "1) 一次只問一個問題\n"
            "2) 問句要精準、簡短、可作答\n"
            "3) 用繁體中文\n"
            "4) 不要透露完整解法\n\n"
            f"第 {step} 輪，難度策略：{difficulty_hint}\n"
            f"上一輪判定：{evaluation}\n"
            f"上一題：{previous_question or '（無）'}\n"
            f"學生上一輪回答：{student_answer or '（無）'}\n"
            f"{grade_hint}"
            f"原題目：{problem}"
        )

        question = self._generate_text(prompt).strip()
        return question or "你先說說看，這題你會先找哪一個已知條件？"

    def generate_final_explanation(
        self,
        *,
        problem: str,
        grade: str | None,
        turns: list[dict[str, str]],
    ) -> str:
        if not self.config.api_key:
            if self.config.allow_mock:
                return self._mock_final_explanation(problem=problem, turns=turns)
            raise GeminiError("GEMINI_API_KEY 未設定")

        grade_hint = f"學生程度：{grade}\n" if grade else ""
        history_text = "\n".join(
            f"第{idx+1}輪｜題：{t['question']}｜答：{t['answer']}｜判定：{t['judgement']}"
            for idx, t in enumerate(turns)
        )

        prompt = (
            "你是教學收斂助教。請根據引導歷程，給出完整詳解。\n"
            "輸出格式：\n"
            "1) 解題關鍵觀念\n"
            "2) 詳細步驟\n"
            "3) 常見錯誤\n"
            "4) 下一題建議\n"
            "請用繁體中文，清楚且鼓勵式語氣。\n\n"
            f"{grade_hint}"
            f"原題目：{problem}\n"
            f"引導歷程：\n{history_text}"
        )
        return self._generate_text(prompt)

    def _generate_text(self, prompt: str) -> str:
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ]
        }

        query = parse.urlencode({"key": self.config.api_key})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent?{query}"
        req = request.Request(
            url=url,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise GeminiError(f"Gemini API HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise GeminiError(f"Gemini API 連線失敗: {exc.reason}") from exc

        text = self._extract_text(body)
        if not text:
            raise GeminiError("Gemini 未回傳可讀內容")
        return text

    @staticmethod
    def _extract_text(raw: dict) -> str | None:
        candidates = raw.get("candidates") or []
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in parts if p.get("text")]
        return "\n".join(text_chunks).strip() or None

    @staticmethod
    def _extract_json(text: str) -> dict:
        cleaned = text.strip()
        if not cleaned:
            return {}

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _mock_evaluation(student_answer: str) -> dict[str, str]:
        answer = student_answer.strip().lower()
        unknown_tokens = ["不知道", "不會", "不会", "不懂", "沒想法", "没想法", "idk", "想不到"]
        if any(token in answer for token in unknown_tokens):
            return {
                "judgement": "dont_know",
                "feedback": "你先不用急，我們先抓最基礎的條件。",
            }

        if len(student_answer.strip()) >= 18:
            return {
                "judgement": "correct",
                "feedback": "方向不錯，我們再往更進階一步。",
            }

        return {
            "judgement": "incorrect",
            "feedback": "你有嘗試，很好！但核心點還差一點，我們先降一階重新確認。",
        }

    @staticmethod
    def _mock_guiding_question(*, problem: str, step: int, difficulty_level: int, evaluation: str) -> str:
        if step == 1:
            return "先不要急著算，你能先說這題已知條件與要找的目標是什麼嗎？"

        if difficulty_level >= 1 or evaluation == "correct":
            return f"第{step}輪進階：如果把這題再變化一個條件，原本方法還成立嗎？為什麼？"

        if evaluation == "dont_know" or difficulty_level <= -1:
            return f"第{step}輪基礎：你先指出題目中最關鍵的一個數字或概念，並說明它代表什麼。"

        return f"第{step}輪：你會選擇哪個公式或原理？請說明理由。"

    @staticmethod
    def _mock_final_explanation(*, problem: str, turns: list[dict[str, str]]) -> str:
        return (
            "以下是完整解析（Mock）：\n"
            "1) 解題關鍵觀念：先辨識已知、未知與可用公式。\n"
            "2) 詳細步驟：依條件代入，逐步檢查每一步是否符合題意。\n"
            "3) 常見錯誤：跳步、單位忽略、把條件看反。\n"
            "4) 下一題建議：嘗試改變其中一個條件，再重新推導一次。\n\n"
            f"原題目：{problem}\n"
            f"已完成引導輪次：{len(turns)}"
        )
