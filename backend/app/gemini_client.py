from __future__ import annotations

import json
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

        prompt = self._build_prompt(question=question, grade=grade)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
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
    def _build_prompt(*, question: str, grade: str | None) -> str:
        grade_hint = f"學生程度：{grade}\n" if grade else ""
        return (
            "你是一位 AI 解題助教，請用繁體中文回答。\n"
            "請先列出解題重點，再給步驟，最後補充常見錯誤。\n"
            "若題目資訊不足，先說明缺什麼資訊。\n\n"
            f"{grade_hint}"
            f"題目：\n{question}"
        )

    @staticmethod
    def _extract_text(raw: dict) -> str | None:
        candidates = raw.get("candidates") or []
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in parts if p.get("text")]
        return "\n".join(text_chunks).strip() or None
