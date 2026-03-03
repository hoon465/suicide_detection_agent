from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict

from .config import load_settings

SYSTEM_PROMPT = """너는 간단한 감정 판별기다.
규칙:
- 반드시 JSON만 출력한다.
- label은 POSITIVE, NEGATIVE, NEUTRAL 중 하나
- confidence는 0~1
출력 스키마:
{"label":"NEUTRAL","confidence":0.0}
"""

IDEATION_SYSTEM_PROMPT = """너는 현재 시점 자살사고 판별기다.
규칙:
- 반드시 JSON만 출력한다.
- 과거가 아니라 '지금 현재 기준'으로 판정한다.
- label은 YES, NO, UNCERTAIN 중 하나
- confidence는 0~1
출력 스키마:
{"label":"UNCERTAIN","confidence":0.0}
"""


# 역할: 시작 발화의 긍정/부정을 LLM으로 판별한다.
def detect_sentiment(user_text: str) -> Dict[str, Any]:
    settings = load_settings()
    model = "gemini-2.5-flash-lite"
    api_key = settings.gemini_api_key

    user_prompt = f"문장: {user_text}\n"

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
            with urllib.request.urlopen(req, timeout=20) as resp:
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
                "label": result.get("label", "NEUTRAL"),
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

    return {"label": "NEUTRAL", "confidence": 0.0}


# 역할: YES/NO 문구가 섞인 발화에서 현재 시점 ideation을 LLM으로 보정 판정한다.
def detect_current_ideation(user_text: str) -> Dict[str, Any]:
    settings = load_settings()
    model = "gemini-2.5-flash-lite"
    api_key = settings.gemini_api_key

    user_prompt = f"문장: {user_text}\n"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {"parts": [{"text": IDEATION_SYSTEM_PROMPT}]},
            {"parts": [{"text": user_prompt}]},
        ],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
    }
    data = json.dumps(payload).encode("utf-8")

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            text_out = (
                parsed.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            result = json.loads(text_out)
            label = str(result.get("label", "UNCERTAIN")).upper()
            if label not in {"YES", "NO", "UNCERTAIN"}:
                label = "UNCERTAIN"
            return {"label": label, "confidence": float(result.get("confidence", 0.0))}
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

    return {"label": "UNCERTAIN", "confidence": 0.0}
