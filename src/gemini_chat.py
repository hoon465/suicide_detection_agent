from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .config import load_settings

SYSTEM_PROMPT = """너는 학생의 감정을 받아주는 대화 파트너다.
규칙:
- 공감 1~2문장
- 제안/행동지시/A-B 선택지 금지
- 질문문 생성 금지
- 존댓말 금지, 편한 반말
- 자해/자살 방법/수단/실행을 돕는 내용 절대 금지
"""


# 역할: LLM 답변에서 질문문을 제거해 규칙을 강제한다.
def _strip_questions(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    kept: List[str] = []
    for ln in lines:
        if "?" in ln or "？" in ln:
            continue
        kept.append(ln)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# 역할: 현재 상태를 바탕으로 공감형 답변을 생성한다.
def generate_reply(
    user_text: str,
    mode: str,
    risk_state: str,
    retrieved_context: List[Dict[str, Any]],
    event_text: str,
    allow_options: int,
) -> str:
    settings = load_settings()
    model = "gemini-2.5-flash-lite"

    context = "\n".join(f"- {s.get('snippet', '')}" for s in retrieved_context[:4])
    user_prompt = (
        f"모드: {mode}\n"
        f"위험상태: {risk_state}\n"
        f"사건요약: {event_text}\n"
        f"사용자 최근발화: {user_text}\n"
        f"선택지 허용 개수: {allow_options}\n"
        f"참고근거:\n{context}\n\n"
        "규칙대로 답변만 작성해. 질문문/선택지/행동지시는 절대 넣지 마."
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [
            {"parts": [{"text": SYSTEM_PROMPT}]},
            {"parts": [{"text": user_prompt}]},
        ],
        "generationConfig": {"temperature": 0.2},
    }

    data = json.dumps(payload).encode("utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            text_out = (
                parsed.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            ).strip()
            text_out = _strip_questions(text_out)
            if text_out:
                return text_out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2**attempt)
                continue
            if attempt == 2:
                break
            time.sleep(2**attempt)
        except Exception:
            if attempt == 2:
                break
            time.sleep(2**attempt)

    # fallback
    return "이야기해줘서 고마워. 네 마음이 얼마나 무거웠는지 느껴져."
