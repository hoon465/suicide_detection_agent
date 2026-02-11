from __future__ import annotations

import re
import unicodedata

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def normalize_text(s: str) -> str:
    text = unicodedata.normalize("NFC", s or "")
    text = ANSI_RE.sub("", text)
    text = CTRL_RE.sub("", text)
    text = text.replace("\u00A0", " ")
    text = text.replace("\u200B", "")
    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    # 자모 분리 입력 노이즈 최소화: 자모/한글 사이 공백 제거
    text = re.sub(r"(?<=[가-힣])\s+(?=[ㄱ-ㅎㅏ-ㅣ])", "", text)
    text = re.sub(r"(?<=[ㄱ-ㅎㅏ-ㅣ])\s+(?=[가-힣])", "", text)
    text = re.sub(r"(?<=[ㄱ-ㅎㅏ-ㅣ])\s+(?=[ㄱ-ㅎㅏ-ㅣ])", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
