from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List

from .config import load_settings

SYSTEM_PROMPT = """너는 자살위험 단서 판별기다.
규칙:
- 반드시 JSON만 출력한다. 추가 설명 금지.
- signal_types는 DIRECT_LANGUAGE, INDIRECT_BEHAVIOR, DIRECT_ACTION 중 선택 가능(복수 가능)
- primary_signal_type은 1개 필수
- evidence_phrases는 사용자 발화에서 그대로 인용, 최대 2개
- '혼자 있어/외로워/우울해'만으로는 signal_hit을 true로 하지 말 것
- signal_hit은 죽음/자살/자해 관련 단서가 있을 때만 true

출력 JSON 스키마:
{"signal_hit":false,"signal_types":[],"primary_signal_type":"INDIRECT_BEHAVIOR","evidence_phrases":[],"confidence":0.0}
"""


def detect_signals(user_text: str, signal_context: str) -> Dict[str, Any]:
    settings = load_settings()
    model = "gemini-2.5-flash-lite"
    api_key = settings.gemini_api_key

    user_prompt = (
        f"사용자 발화: {user_text}\n\n"
        f"참고 단서 텍스트:\n{signal_context}\n"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {"parts": [{"text": SYSTEM_PROMPT}]},
            {"parts": [{"text": user_prompt}]},
        ],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
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
            )
            result = json.loads(text_out)
            return {
                "signal_hit": bool(result.get("signal_hit", False)),
                "signal_types": result.get("signal_types", []) or [],
                "primary_signal_type": result.get("primary_signal_type", "INDIRECT_BEHAVIOR"),
                "evidence_phrases": result.get("evidence_phrases", []) or [],
                "confidence": float(result.get("confidence", 0.0)),
            }
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == 2:
                break
            time.sleep(2 ** attempt)

    return {
        "signal_hit": False,
        "signal_types": [],
        "primary_signal_type": "INDIRECT_BEHAVIOR",
        "evidence_phrases": [],
        "confidence": 0.0,
    }
