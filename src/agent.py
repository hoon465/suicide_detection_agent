from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .gemini_chat import generate_reply
from .memory import add_qa, init_memory, set_slot
from .question_bank import get_question
from .scoring import (
    compute_scores,
    parse_freq,
    parse_past_response,
    parse_plan_level,
    parse_urgency,
    parse_yes_no,
)
from .schemas import empty_turn
from .sentiment_detector import detect_current_ideation, detect_sentiment
from .summarizer import build_final_one_liner, build_structured_fields, natural_summary_from_structured
from .utils import normalize_text


# 역할: 에이전트 런타임 상태를 초기화한다.
def init_state() -> Dict[str, Any]:
    return {
        "mode": "START_WAIT",
        "question_key": "Q_START",
        "memory": init_memory(),
        "prev_pain": 0,
        "prev_suicide": 0,
        "turn_index": 0,
        "store_raw_text": False,
    }


# 역할: 첫 응답이 긍정 흐름인지 판별한다.
def _is_positive_text(user_text: str) -> bool:
    sentiment = detect_sentiment(user_text)
    return sentiment.get("label") == "POSITIVE"


# 역할: 위험 상태에 따른 외부 지원 리소스를 결정한다.
def _escalation_for_state(risk_state: str) -> Dict[str, Any]:
    if risk_state == "S2":
        return {
            "필요": True,
            "유형": "soft_connect",
            "리소스": [
                {"name": "자살예방상담 109", "how": "전화", "notes": "24시간"},
                {"name": "청소년전화 1388", "how": "전화", "notes": "청소년 상담"},
            ],
        }
    if risk_state == "S3":
        return {
            "필요": True,
            "유형": "urgent_connect",
            "리소스": [
                {"name": "자살예방상담 109", "how": "전화", "notes": "24시간"},
                {"name": "청소년전화 1388", "how": "전화", "notes": "청소년 상담"},
                {"name": "112/119", "how": "전화", "notes": "긴급"},
            ],
        }
    return {"필요": False, "유형": "none", "리소스": []}


# 역할: ideation=NO일 때 사건 기반 마무리 메시지를 만든다.
def _build_event_based_close_message(event_text: str) -> str:
    if event_text:
        return (
            f"{event_text} 같은 일을 겪으면 마음이 크게 흔들릴 수 있어. "
            "오늘은 잠들기 전에 네 편이 되어줄 수 있는 사람 한 명에게 짧게라도 연락해보자. "
            "지금까지 잘 버텨줘서 고마워."
        )
    return "마음이 힘들었겠어. 오늘은 네 편이 되어줄 사람 한 명에게 짧게라도 연락해보자. 지금까지 잘 버텨줘서 고마워."


# 역할: 종료 시 사용자에게 보여줄 최종 안내 문장을 만든다.
def _build_final_user_message(structured_fields: Dict[str, Any]) -> str:
    lines: List[str] = [
        "여기까지 솔직하게 말해줘서 고마워. 네가 버티느라 얼마나 힘들었는지 느껴져.",
    ]
    level = structured_fields.get("referral_level", "none")
    if structured_fields.get("final_risk_state") in {"S2", "S3"}:
        lines.append("지금은 혼자 버티지 말고 109나 1388에 바로 연결해보자.")
    if level in {"needs_specialist_referral", "extreme_crisis"}:
        lines.append("지금 단계에서는 전문가 도움을 꼭 받는 게 좋아.")
    if level == "extreme_crisis":
        lines.append("지금은 절대 혼자 있지 말고 보호자에게 바로 알리고, 필요하면 112/119에 즉시 연락해.")
    return " ".join(lines)


# 역할: 현재 모드와 슬롯값으로 다음 모드/질문/종료 여부를 결정한다.
def _route(mode: str, normalized_user_text: str, memory: Dict[str, Any]) -> Tuple[str, str, bool, str]:
    if mode == "START_WAIT":
        if _is_positive_text(normalized_user_text):
            return "POS_EVENT_WAIT", "Q_POS_EVENT", False, "none"
        return "EVENT_WAIT", "Q_EVENT", False, "none"

    if mode == "POS_EVENT_WAIT":
        return "END", "", True, "user_positive_close"

    if mode == "EVENT_WAIT":
        return "IDEATION_WAIT", "Q_IDEATION", False, "none"

    if mode == "IDEATION_WAIT":
        ideation = memory.get("ideation")
        if ideation is False:
            return "END", "", True, "resolved"
        if ideation is True:
            return "FREQ_WAIT", "Q_FREQ", False, "none"
        return "IDEATION_WAIT", "Q_IDEATION", False, "none"

    if mode == "FREQ_WAIT":
        return "PLAN_WAIT", "Q_PLAN_LEVEL", False, "none"
    if mode == "PLAN_WAIT":
        return "URGENCY_WAIT", "Q_URGENCY", False, "none"
    if mode == "URGENCY_WAIT":
        return "PAST_WAIT", "Q_PAST", False, "none"
    if mode == "PAST_WAIT":
        return "FAMILY_WAIT", "Q_FAMILY_SUICIDE", False, "none"
    if mode == "FAMILY_WAIT":
        return "END", "", True, "questionnaire_complete"

    return "END", "", True, "resolved"


# 역할: 현재 질문 키에 맞게 사용자 응답을 슬롯에 반영한다.
def _update_slots_from_answer(question_key: str, answer_text: str, memory: Dict[str, Any]) -> None:
    if question_key == "Q_EVENT":
        set_slot(memory, "event_text", answer_text)
    elif question_key == "Q_IDEATION":
        set_slot(memory, "ideation_resolution", "none")
        llm_out = detect_current_ideation(answer_text)
        label = str(llm_out.get("label", "UNCERTAIN")).upper()
        if label == "YES":
            set_slot(memory, "ideation", True)
            set_slot(memory, "ideation_resolution", "llm")
        elif label == "NO":
            set_slot(memory, "ideation", False)
            set_slot(memory, "ideation_resolution", "llm")
        else:
            # LLM이 확신하지 못하면 기존 키워드 룰로만 보조 판정
            yn = parse_yes_no(answer_text)
            if yn is not None:
                set_slot(memory, "ideation", yn)
                set_slot(memory, "ideation_resolution", "llm_fallback_rule")
            else:
                set_slot(memory, "ideation_resolution", "llm_uncertain")
    elif question_key == "Q_FREQ":
        val = parse_freq(answer_text)
        if val:
            set_slot(memory, "freq", val)
    elif question_key == "Q_PLAN_LEVEL":
        val = parse_plan_level(answer_text)
        if val:
            set_slot(memory, "plan_level", val)
    elif question_key == "Q_URGENCY":
        set_slot(memory, "urgency", parse_urgency(answer_text))
    elif question_key == "Q_PAST":
        ideation_yes, attempt_yes, category = parse_past_response(answer_text)
        set_slot(memory, "past_ideation_yes", ideation_yes)
        set_slot(memory, "past_attempt_yes", attempt_yes)
        set_slot(memory, "past_category", category)
        set_slot(memory, "past_text", answer_text)
    elif question_key == "Q_FAMILY_SUICIDE":
        yn = parse_yes_no(answer_text)
        if yn is not None:
            set_slot(memory, "family_suicide", yn)


# 역할: 디버깅용 핵심 상태만 추려 compact_debug를 만든다.
def _build_compact_debug(result: Dict[str, Any], state: Dict[str, Any], memory: Dict[str, Any]) -> Dict[str, Any]:
    sf = (result.get("대화제어", {}).get("summary_if_end", {}) or {}).get("structured_fields", {})
    checklist_hits = sf.get("checklist_hits", []) if isinstance(sf, dict) else []
    last_q_key = result.get("기억", {}).get("마지막_qna", {}).get("q_key", "")
    next_q_key = result.get("행동", {}).get("질문_유형", "")

    return {
        "turn": int(state.get("turn_index", 0)),
        "last_q_key": last_q_key,
        "next_q_key": next_q_key,
        "risk": result.get("모니터링", {}).get("risk_state", "S0"),
        "suicide": result.get("모니터링", {}).get("자살_신호_점수", 0),
        "pain": result.get("모니터링", {}).get("정서적_고통_점수", 0),
        "freq": memory.get("freq", ""),
        "plan": memory.get("plan_level", ""),
        "urgency": memory.get("urgency", ""),
        "past_attempt_yes": bool(memory.get("past_attempt_yes") is True),
        "ideation_resolution": memory.get("ideation_resolution", "none"),
        "checklist_hits": checklist_hits,
        "referral_level": sf.get("referral_level", ""),
        "end_reason": result.get("대화제어", {}).get("종료_이유", "none"),
    }


# 역할: 한 턴 전체 처리(업데이트/점수/질문/종료요약)를 수행한다.
def run_turn(state: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    result = empty_turn()

    raw_text = user_text
    normalized_user_text = normalize_text(user_text)

    mode = state.get("mode", "START_WAIT")
    question_key = state.get("question_key", "Q_START")
    memory = state.get("memory", init_memory())

    current_question = get_question(question_key)
    add_qa(memory, question_key, current_question, normalized_user_text)
    _update_slots_from_answer(question_key, normalized_user_text, memory)

    scores = compute_scores(
        memory=memory,
        user_text=normalized_user_text,
        prev_pain=int(state.get("prev_pain", 0)),
        prev_suicide=int(state.get("prev_suicide", 0)),
        question_key=question_key,
    )
    state["prev_pain"] = scores["pain_score"]
    state["prev_suicide"] = scores["suicide_score"]

    monitoring = {
        "정서적_고통_점수": scores["pain_score"],
        "정서적_고통_상태": scores["pain_level"],
        "자살_신호_점수": scores["suicide_score"],
        "자살_신호_상태": scores["suicide_level"],
        "risk_state": scores["risk_state"],
        "근거": scores["rationale"],
    }
    result["모니터링"] = monitoring

    next_mode, next_question_key, should_end, end_reason = _route(mode, normalized_user_text, memory)

    if mode in {"START_WAIT", "POS_EVENT_WAIT", "EVENT_WAIT"}:
        assistant_message = "네 얘기 잘 들었어."
    else:
        try:
            assistant_message = generate_reply(
                user_text=normalized_user_text,
                mode=mode,
                risk_state=monitoring["risk_state"],
                retrieved_context=[],
                event_text=memory.get("event_text", ""),
                allow_options=0,
            )
        except Exception:
            assistant_message = "네 얘기 잘 들었어."

    if mode == "IDEATION_WAIT" and memory.get("ideation") is False:
        assistant_message = _build_event_based_close_message(memory.get("event_text", ""))

    result["답변"] = assistant_message

    next_question = "" if should_end else get_question(next_question_key)
    result["행동"]["다음_질문"] = next_question
    result["행동"]["질문_유형"] = next_question_key
    result["행동"]["제안"] = []
    result["행동"]["에스컬레이션"] = _escalation_for_state(monitoring["risk_state"])

    state["turn_index"] = int(state.get("turn_index", 0)) + 1
    result["기억"] = {
        "turn_index": state["turn_index"],
        "transcript_len": len(memory.get("transcript", [])),
        "마지막_qna": memory.get("transcript", [])[-1],
    }

    state["mode"] = next_mode
    state["question_key"] = next_question_key
    memory["scoring_breakdown"] = scores["breakdown"]
    memory["triggers"] = scores["breakdown"].get("triggers", {"TR1": False, "TR2": False})
    state["memory"] = memory

    if should_end:
        final_scores = compute_scores(
            memory=memory,
            user_text=normalized_user_text,
            prev_pain=int(state.get("prev_pain", 0)),
            prev_suicide=int(state.get("prev_suicide", 0)),
            question_key="FINAL",
        )
        monitoring["정서적_고통_점수"] = final_scores["pain_score"]
        monitoring["정서적_고통_상태"] = final_scores["pain_level"]
        monitoring["자살_신호_점수"] = final_scores["suicide_score"]
        monitoring["자살_신호_상태"] = final_scores["suicide_level"]
        monitoring["risk_state"] = final_scores["risk_state"]

        structured_fields = build_structured_fields(
            memory,
            monitoring,
            final_scores["breakdown"],
        )
        if state.get("store_raw_text"):
            structured_fields["raw_text"] = raw_text

        try:
            natural_summary = natural_summary_from_structured(structured_fields)
        except Exception:
            natural_summary = "대화 요약 생성에 실패해 구조화 요약만 남겼어."

        final_one_liner = build_final_one_liner(structured_fields)

        result["답변"] = _build_final_user_message(structured_fields)
        result["대화제어"]["종료"] = True
        result["대화제어"]["종료_이유"] = end_reason
        result["대화제어"]["summary_if_end"] = {
            "structured_fields": structured_fields,
            "natural_summary": natural_summary,
            "final_one_liner": final_one_liner,
        }
        result["대화제어"]["FINAL"] = f"FINAL: {final_one_liner}"

    result["compact_debug"] = _build_compact_debug(result, state, memory)
    return result
