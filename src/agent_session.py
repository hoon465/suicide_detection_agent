from __future__ import annotations

from typing import Any, Dict, List

from .agent import init_state, run_turn
from .question_bank import get_question
from .schemas import empty_turn
from .utils import normalize_text


class AgentSession:
    def __init__(self) -> None:
        self.state: Dict[str, Any] = init_state()
        self.turns: List[Dict[str, Any]] = []

    def start_turn(self) -> Dict[str, Any]:
        first = empty_turn()
        first["답변"] = ""
        first["행동"]["질문_유형"] = "Q_START"
        first["행동"]["다음_질문"] = get_question("Q_START")
        self.turns.append(first)
        return first

    def process_user_text(self, user_text: str) -> Dict[str, Any]:
        normalized = normalize_text(user_text)
        result = run_turn(self.state, normalized)
        self.turns.append(result)
        return result

    def get_turns(self) -> List[Dict[str, Any]]:
        return list(self.turns)
