from __future__ import annotations

from typing import Dict

QUESTION_BANK: Dict[str, str] = {
    "Q_START": "오늘 하루는 어땠어?",
    "Q_POS_EVENT": "좋았던 일 중에 오늘 가장 기억에 남는 건 뭐였어?",
    "Q_EVENT": "오늘이나 최근에 마음을 크게 힘들게 한 안 좋은 일이 있었어? 있었다면 어떤 일이었는지 말해줘.",
    "Q_IDEATION": "죽고 싶다는 생각도 들었어?",
    "Q_FREQ": "요즘 죽고 싶다는 생각이 얼마나 자주 들어? (자주/가끔/거의 안)",
    "Q_PLAN_LEVEL": "그 생각이 들 때, 막연한 생각이야 아니면 계획까지 세워진 느낌이야? (A막연/B어느정도/C구체)",
    "Q_URGENCY": "그게 오늘/곧바로 실행될 것 같아, 아니면 당장은 아니야? (오늘/당장아님)",
    "Q_PAST": "이전에도 죽고 싶다고 생각했거나 실제로 시도한 적 있어?",
    "Q_FAMILY_SUICIDE": "혹시 가족이나 정말 가까운 사람이 자살로 세상을 떠난 적이 있어?",
}


def get_question(question_key: str) -> str:
    return QUESTION_BANK.get(question_key, "지금 가장 마음에 걸리는 게 뭐야?")
