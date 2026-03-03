from __future__ import annotations

from typing import Any, Dict


# 역할: 턴별 JSON 출력의 기본 스키마를 생성한다.
def empty_turn() -> Dict[str, Any]:
    return {
        "답변": "",
        "모니터링": {
            "정서적_고통_점수": 0,
            "정서적_고통_상태": "낮음",
            "자살_신호_점수": 0,
            "자살_신호_상태": "낮음",
            "risk_state": "S0",
            "근거": [],
        },
        "행동": {
            "다음_질문": "",
            "질문_유형": "",
            "제안": [],
            "에스컬레이션": {
                "필요": False,
                "유형": "none",
                "리소스": [],
            },
        },
        "기억": {
            "turn_index": 0,
            "transcript_len": 0,
            "마지막_qna": {"q": "", "a": ""},
        },
        "compact_debug": {
            "turn": 0,
            "last_q_key": "",
            "next_q_key": "",
            "risk": "S0",
            "suicide": 0,
            "pain": 0,
            "freq": "",
            "plan": "",
            "urgency": "",
            "past_attempt_yes": False,
            "ideation_resolution": "none",
            "checklist_hits": [],
            "referral_level": "",
            "end_reason": "none",
        },
        "대화제어": {
            "종료": False,
            "종료_이유": "none",
            "summary_if_end": None,
            "FINAL": None,
        },
    }
