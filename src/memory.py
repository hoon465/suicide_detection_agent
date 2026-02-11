from __future__ import annotations

from typing import Any, Dict, List


def init_memory() -> Dict[str, Any]:
    return {
        "event_text": "",
        "ideation": None,
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


def add_qa(memory: Dict[str, Any], question_key: str, question_text: str, answer_text: str) -> None:
    memory.setdefault("transcript", []).append(
        {"q_key": question_key, "q": question_text, "a": answer_text}
    )


def set_slot(memory: Dict[str, Any], key: str, value: Any) -> None:
    memory[key] = value


def get_transcript(memory: Dict[str, Any]) -> List[Dict[str, str]]:
    return list(memory.get("transcript", []))
