from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

PAIN_KEYWORDS: List[Tuple[str, int]] = [
    ("우울", 20),
    ("힘들", 20),
    ("괴롭", 20),
    ("불안", 20),
    ("외롭", 20),
    ("무섭", 20),
    ("짜증", 20),
    ("화나", 20),
    ("눈물", 20),
]

INTENSIFIERS: List[Tuple[str, int]] = [
    ("너무", 10),
    ("진짜", 10),
    ("정말", 10),
    ("죽을만큼", 10),
    ("견딜 수", 10),
]

EVENT_SEVERITY_KEYWORDS: List[Tuple[str, int]] = [
    ("왕따", 30),
    ("따돌림", 30),
    ("괴롭힘", 30),
    ("폭력", 30),
    ("학대", 30),
    ("욕", 25),
    ("협박", 30),
    ("성폭력", 30),
    ("가정폭력", 30),
]

SUICIDE_PHRASES: List[Tuple[str, int]] = [
    ("죽고 싶", 25),
    ("죽고싶", 25),
    ("죽어버리고 싶", 30),
    ("사라지고 싶", 18),
    ("끝내고 싶", 20),
    ("살기 싫", 22),
    ("그만하고 싶", 15),
    ("자살", 30),
    ("자해", 25),
]

SEVERE_EVENT_KEYWORDS: List[str] = [
    "왕따", "따돌림", "괴롭힘", "폭력", "학대", "성폭력", "가정폭력", "사망", "죽었", "퇴학", "정학", "법적", "가출", "위협", "사고", "경제위기",
]

NO_SUBSTRINGS: List[str] = [
    "아니", "없어", "없음", "안 들어", "안들어", "괜찮", "죽고 싶지", "죽고 싶진", "죽고싶지", "죽고싶진", "않았", "안 했", "안했", "당장은 아니",
]

YES_SUBSTRINGS: List[str] = [
    "yes", "응", "어", "예", "맞아", "있어", "있음", "죽고 싶", "죽고싶", "들더라", "들었어", "시도한 적 있어", "있다",
]


# 역할: 점수를 0~100 범위로 제한한다.
def _clamp(v: int) -> int:
    return max(0, min(100, v))


# 역할: 고통 점수를 사람이 읽기 쉬운 단계로 변환한다.
def _pain_state(score: int) -> str:
    if score >= 70:
        return "높음"
    if score >= 50:
        return "중간"
    if score >= 20:
        return "경도"
    return "낮음"


# 역할: 자살 점수와 트리거로 최종 위험 상태를 결정한다.
def _state_from_suicide_score(base_score: int, triggers: Dict[str, bool]) -> str:
    # A) risk_state는 suicide_score(base_score) 기준으로만 판정
    if base_score >= 80:
        state = "S3"
    elif base_score >= 50:
        state = "S2"
    elif base_score >= 20:
        state = "S1"
    else:
        state = "S0"

    # trigger는 최소 리스크 강제 상향만 수행
    if triggers.get("TR1") or triggers.get("TR2"):
        state = "S3"
    return state


# 역할: 자연어 응답을 예/아니오 불리언으로 파싱한다.
def parse_yes_no(text: str) -> Optional[bool]:
    lower = text.lower().strip()
    if any(s in lower for s in NO_SUBSTRINGS):
        return False
    if any(s in lower for s in YES_SUBSTRINGS):
        return True
    return None


# 역할: 예/아니오 키워드 동시 검출 여부를 함께 반환한다.
def parse_yes_no_with_flags(text: str) -> Tuple[Optional[bool], bool, bool]:
    lower = text.lower().strip()
    has_no = any(s in lower for s in NO_SUBSTRINGS)
    has_yes = any(s in lower for s in YES_SUBSTRINGS)
    return parse_yes_no(text), has_yes, has_no


# 역할: 빈도 응답을 자주/가끔/거의 안으로 정규화한다.
def parse_freq(text: str) -> str:
    lower = text.lower()
    if "자주" in lower or "자주들" in lower or "자주임" in lower or "매일" in lower or "계속" in lower:
        return "자주"
    if "가끔" in lower or "종종" in lower or "때때로" in lower:
        return "가끔"
    if "거의 안" in lower or "드물" in lower:
        return "거의 안"
    return ""


# 역할: 계획 수준 응답을 A/B/C로 정규화한다.
def parse_plan_level(text: str) -> str:
    lower = text.lower().strip()
    if "c" in lower or "구체" in lower or "계획 세워" in lower or "언제" in lower or "어디서" in lower:
        return "C"
    if "b" in lower or "어느정도" in lower:
        return "B"
    if "a" in lower or "막연" in lower:
        return "A"
    return ""


# 역할: 긴급성 응답을 오늘/곧바로 또는 당장아님으로 파싱한다.
def parse_urgency(text: str) -> str:
    lower = text.lower().strip()
    not_now_patterns = [
        "당장은 아니", "지금은 아니", "바로는 아니", "오늘은 아니", "곧은 아니", "아직은 아니", "지금 당장 아니", "당장아님",
    ]
    if any(p in lower for p in not_now_patterns):
        return "당장아님"

    immediate_patterns = ["지금 당장", "오늘", "곧바로", "바로", "지금 할 것 같"]
    if any(p in lower for p in immediate_patterns):
        return "오늘/곧바로"

    return "당장아님"


# 역할: 과거력 응답에서 생각/시도 여부를 분리 판정한다.
def parse_past_response(text: str) -> Tuple[bool, bool, str]:
    lower = text.lower().strip()

    attempt_yes = False
    ideation_yes = False
    category = "none"

    if "시도" in lower and not any(k in lower for k in ["안 했", "안했", "없어", "없음"]):
        attempt_yes = True
        ideation_yes = True
        category = "attempt"
        return ideation_yes, attempt_yes, category

    if any(k in lower for k in ["생각", "죽고 싶", "죽고싶", "뛰어내릴까", "사라지고 싶", "살기 싫"]):
        if any(k in lower for k in ["없어", "없음", "안 해", "안했", "아니"]):
            return False, False, "none"
        ideation_yes = True
        category = "ideation_only"
        return ideation_yes, attempt_yes, category

    yn = parse_yes_no(lower)
    if yn is True:
        return True, False, "ideation_only"
    if yn is False:
        return False, False, "none"
    return False, False, "none"


# 역할: 사건 텍스트를 severe/mild/none로 분류한다.
def classify_event_severity(event_text: str) -> str:
    if not event_text:
        return "none"
    lower = event_text.lower()
    if any(k in lower for k in SEVERE_EVENT_KEYWORDS):
        return "severe"
    if any(k in lower for k in ["시험", "피곤", "짜증", "스트레스"]):
        return "mild"
    return "mild"


# 역할: 감정/사건 키워드로 고통 점수를 계산한다.
def pain_score_from_text(user_text: str, event_text: str) -> Tuple[int, Dict[str, int]]:
    lower_user = user_text.lower()
    lower_event = event_text.lower()
    score = 0
    breakdown: Dict[str, int] = {}

    for kw, w in PAIN_KEYWORDS:
        if kw in lower_user or kw in lower_event:
            score += w
            breakdown[f"pain:{kw}"] = w

    for kw, w in INTENSIFIERS:
        if kw in lower_user or kw in lower_event:
            score += w
            breakdown[f"intensity:{kw}"] = w

    for kw, w in EVENT_SEVERITY_KEYWORDS:
        if kw in lower_user or kw in lower_event:
            score += w
            breakdown[f"event:{kw}"] = w

    return _clamp(score), breakdown


# 역할: 문진 슬롯 기반으로 자살 신호 점수를 가중치 합산한다.
def suicide_score_weighted(memory: Dict[str, Any], user_text: str) -> Tuple[int, Dict[str, int]]:
    score = 0
    breakdown: Dict[str, int] = {}

    ideation = memory.get("ideation")
    freq = memory.get("freq", "")
    plan = memory.get("plan_level", "")
    urgency = memory.get("urgency", "")
    past_attempt_yes = bool(memory.get("past_attempt_yes") is True)

    if ideation is True:
        score += 30
        breakdown["Q_IDEATION(YES)"] = 30

    if freq == "자주":
        score += 20
        breakdown["Q_FREQ(자주)"] = 20
    elif freq == "가끔":
        score += 10
        breakdown["Q_FREQ(가끔)"] = 10
    elif freq == "거의 안":
        score += 5
        breakdown["Q_FREQ(거의안)"] = 5

    if plan == "A":
        score += 5
        breakdown["Q_PLAN(A)"] = 5
    elif plan == "B":
        score += 15
        breakdown["Q_PLAN(B)"] = 15
    elif plan == "C":
        score += 30
        breakdown["Q_PLAN(C)"] = 30

    if urgency == "오늘/곧바로":
        score += 30
        breakdown["Q_URGENCY(오늘/곧바로)"] = 30
    elif urgency == "당장아님":
        breakdown["Q_URGENCY(당장아님)"] = 0

    if past_attempt_yes:
        score += 25
        breakdown["Q_PAST_ATTEMPT(YES)"] = 25

    # ideation 이전 보조 lexical 판단
    if ideation is not True:
        lower_all = " ".join([
            str(memory.get("event_text", "")),
            " ".join(str(x.get("a", "")) for x in memory.get("transcript", [])[-5:]),
            user_text,
        ]).lower()
        lexical = 0
        for kw, w in SUICIDE_PHRASES:
            if kw in lower_all:
                lexical = max(lexical, w)
        if lexical > 0:
            score += lexical
            breakdown["lexical_suicide_phrase"] = lexical

    return _clamp(score), breakdown


# 역할: 한 턴의 pain/suicide/risk 상태를 통합 계산한다.
def compute_scores(
    memory: Dict[str, Any],
    user_text: str,
    prev_pain: int,
    prev_suicide: int,
    question_key: str = "",
) -> Dict[str, Any]:
    pain_curr, pain_breakdown = pain_score_from_text(user_text, memory.get("event_text", ""))
    suicide_curr, suicide_breakdown = suicide_score_weighted(memory, user_text)

    # 점수 단조 증가
    pain = _clamp(max(prev_pain, pain_curr))
    suicide = _clamp(max(prev_suicide, suicide_curr))

    triggers = {"TR1": False, "TR2": False}
    if memory.get("urgency") == "오늘/곧바로":
        triggers["TR1"] = True
    if memory.get("plan_level") == "C" and memory.get("freq") == "자주":
        triggers["TR2"] = True

    risk_state = _state_from_suicide_score(suicide, triggers)

    rationale: List[str] = []
    rationale.extend(pain_breakdown.keys())
    rationale.extend(suicide_breakdown.keys())
    if triggers["TR1"]:
        rationale.append("trigger:TR1")
    if triggers["TR2"]:
        rationale.append("trigger:TR2")

    return {
        "pain_score": pain,
        "suicide_score": suicide,
        "pain_level": _pain_state(pain),
        "suicide_level": _pain_state(suicide),
        "risk_state": risk_state,
        "rationale": rationale,
        "breakdown": {
            "pain": pain_breakdown,
            "suicide": suicide_breakdown,
            "triggers": triggers,
            "debug_only_suicide_base_score": suicide,
        },
    }
