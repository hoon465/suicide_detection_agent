from __future__ import annotations

from typing import Any, Dict, List

from .agent import init_state, run_turn
from .question_bank import get_question
from .schemas import empty_turn
from .utils import normalize_text


# 역할: 대화 세션 상태를 보관하고 턴 실행을 중계한다.
class AgentSession:
    # 역할: 세션 내부 상태와 턴 기록 저장소를 초기화한다.
    def __init__(self) -> None:
        self.state: Dict[str, Any] = init_state()
        self.turns: List[Dict[str, Any]] = []

    # 역할: 대화 시작용 첫 질문 턴을 생성한다.
    def start_turn(self) -> Dict[str, Any]:
        first = empty_turn()
        first["답변"] = ""
        first["행동"]["질문_유형"] = "Q_START"
        first["행동"]["다음_질문"] = get_question("Q_START")
        self.turns.append(first)
        return first

    # 역할: 사용자 입력 1건을 처리해 한 턴 결과를 반환한다.
    def process_user_text(self, user_text: str) -> Dict[str, Any]:
        normalized = normalize_text(user_text)
        result = run_turn(self.state, normalized)
        self.turns.append(result)
        return result

    # 역할: 현재까지 누적된 턴 결과를 반환한다.
    def get_turns(self) -> List[Dict[str, Any]]:
        return list(self.turns)
