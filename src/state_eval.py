from __future__ import annotations

import re
from typing import Dict, List, Tuple

PAIN_KEYWORDS: List[Tuple[str, int]] = [
    ("힘들", 20),
    ("지쳐", 20),
    ("괴로", 25),
    ("외롭", 20),
    ("불안", 15),
    ("우울", 20),
    ("눈물", 15),
    ("무기력", 20),
    ("스트레스", 15),
    ("무시", 15),
    ("험담", 15),
    ("따돌", 20),
    ("괴롭", 20),
]

SUICIDE_KEYWORDS: List[Tuple[str, int]] = [
    ("죽고 싶", 60),
    ("죽어버리고 싶", 65),
    ("사라지고 싶", 40),
    ("끝내고 싶", 50),
    ("살기 싫", 55),
    ("그만하고 싶", 40),
    ("죽을래", 70),
    ("자살", 80),
    ("그만 살", 70),
    ("자해", 60),
    ("손목", 60),
    ("뛰어내", 90),
    ("오늘 밤", 30),
    ("지금 당장", 40),
]

DOWNPLAY_PATTERNS = [r"농담", r"장난", r"아냐", r"별\s*거\s*아냐"]
FREQ_PATTERNS = [r"자주", r"자주", r"자꾸", r"계속", r"매일", r"가끔", r"종종", r"때때로"]
INTENSITY_PATTERNS = [r"0\s*~\s*10", r"0-10", r"강도", r"정도"]


def _clamp(v: int) -> int:
    return max(0, min(100, v))


def _level(score: int) -> str:
    if score >= 80:
        return "매우높음"
    if score >= 60:
        return "높음"
    if score >= 30:
        return "중간"
    return "낮음"


def _contains_any(patterns: List[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def _is_freq_intensity_reply(text: str) -> bool:
    return _contains_any(FREQ_PATTERNS, text) or _contains_any(INTENSITY_PATTERNS, text)


def evaluate_state(history: List[Dict[str, int]], user_text: str, ideation_yes: bool) -> Dict[str, any]:
    lower = user_text.strip().lower()
    pain = 0
    suicide = 0
    rationale: List[str] = []

    for kw, score in PAIN_KEYWORDS:
        if kw in lower:
            pain += score
            rationale.append(f"pain:{kw}")

    for kw, score in SUICIDE_KEYWORDS:
        if kw in lower:
            suicide += score
            rationale.append(f"suicide:{kw}")

    pain = _clamp(pain)
    suicide = _clamp(suicide)

    # carry-over decay
    prev = history[-1] if history else None
    if prev:
        pain = max(pain, round(prev.get("pain", 0) * 0.85))
        suicide = max(suicide, round(prev.get("suicide", 0) * 0.90))

    # if ideation already yes, frequency/intensity answers should not drop suicide
    if ideation_yes and _is_freq_intensity_reply(lower):
        suicide = max(suicide, prev.get("suicide", 0) if prev else suicide)

    # recent S2+ keeps a floor
    recent_s2plus = any(h.get("risk_state") in ("S2", "S3") for h in history[-3:])
    if recent_s2plus and suicide < 35:
        suicide = 35

    if suicide >= 80:
        state = "S3"
    elif suicide >= 40:
        state = "S2"
    elif pain >= 60:
        state = "S1"
    else:
        state = "S0"

    return {
        "emotional_pain_score": pain,
        "emotional_pain_level": _level(pain),
        "suicide_signal_score": suicide,
        "suicide_signal_level": _level(suicide),
        "risk_state": state,
        "risk_rationale": rationale,
    }


def is_end_intent(text: str) -> bool:
    return _contains_any([r"고마워", r"괜찮아", r"이제\s*됐", r"나갈게", r"그만할게"], text)


def is_safety_confirm(text: str) -> bool:
    return _contains_any([r"전화할게", r"연락할게", r"옆에\s*있", r"혼자\s*아니", r"지금\s*안전"], text)


def is_handoff(text: str) -> bool:
    return _contains_any([r"연락할게", r"상담", r"연계", r"도움\s*받을게"], text)
