from __future__ import annotations

from typing import Any, Dict, List


# 역할: 대화 중 누적할 메모리(슬롯/트랜스크립트)를 초기화한다.
def init_memory() -> Dict[str, Any]:
    return {
        "event_text": "",
        "ideation": None,
        "ideation_resolution": "none",
        "freq": "",
        "plan_level": "",
        "urgency": "",
        "past_attempt_yes": False,
        "past_ideation_yes": False,
        "past_text": "",
        "past_category": "none",
        "family_suicide": None,
        "transcript": [],
        "scoring_breakdown": {},
        "triggers": {"TR1": False, "TR2": False},
    }


# 역할: 현재 턴 질문과 사용자 답변을 transcript에 기록한다.
def add_qa(memory: Dict[str, Any], question_key: str, question_text: str, answer_text: str) -> None:
    memory.setdefault("transcript", []).append(
        {"q_key": question_key, "q": question_text, "a": answer_text}
    )


# 역할: 슬롯 형태의 상태값을 메모리에 저장한다.
def set_slot(memory: Dict[str, Any], key: str, value: Any) -> None:
    memory[key] = value


# 역할: 누적된 질문-답변 기록을 복사해 반환한다.
def get_transcript(memory: Dict[str, Any]) -> List[Dict[str, str]]:
    return list(memory.get("transcript", []))
