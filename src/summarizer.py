from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .config import load_settings
from .utils import normalize_text

CL5_EVENT_KEYWORDS: Dict[str, List[str]] = {
    "school_peer": [
        "왕따", "따돌림", "괴롭힘", "bullying", "놀림", "조롱", "폭언", "모욕", "소문", "험담",
        "단톡방", "카톡", "사이버", "sns", "인스타", "디엠", "댓글", "폭행", "싸움", "협박",
        "갈취", "금품", "강요", "성희롱", "성추행", "촬영", "유포",
    ],
    "family_guardian": [
        "부모", "가족", "집", "가정", "이혼", "별거", "가출", "학대", "방임", "폭력", "폭언",
        "술", "알코올", "도박", "경제", "빚", "생활비", "체벌", "통제", "감금",
    ],
    "relationship": [
        "헤어짐", "이별", "차였", "잠수", "바람", "환승", "스토킹", "집착", "협박", "폭로",
        "유출", "폭언",
    ],
    "loss_incident": [
        "사망", "죽음", "장례", "사고", "교통사고", "중환자", "병원", "암", "중병", "실종",
        "범죄", "신고", "경찰", "재판",
    ],
    "study_career_pressure": [
        "성적", "시험", "입시", "수능", "재수", "유급", "퇴학", "정학", "처벌", "생활기록부",
        "선생님", "학원", "압박", "부담", "실패", "낙제",
    ],
    "economic_life": [
        "돈", "해고", "알바", "실직", "파산", "압류", "월세", "계약", "빚", "사기",
    ],
}


# 역할: Q_EVENT 텍스트에서 CL5 키워드/카테고리 히트를 추출한다.
def _detect_cl5_from_event(event_text: str) -> Dict[str, Any]:
    normalized = normalize_text(event_text).lower()
    categories_hit: List[str] = []
    keywords_hit: List[str] = []

    for category, keywords in CL5_EVENT_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in normalized]
        if matched:
            categories_hit.append(category)
            for kw in matched:
                if kw not in keywords_hit:
                    keywords_hit.append(kw)
                if len(keywords_hit) >= 5:
                    break
        if len(keywords_hit) >= 5:
            break

    return {
        "event_categories_hit": categories_hit,
        "event_keywords_hit": keywords_hit[:5],
        "checklist_5_hit": bool(categories_hit),
    }


# 역할: 체크리스트 1~6 히트 여부와 의뢰 수준을 계산한다.
def evaluate_checklist_hits(memory: Dict[str, Any], final_risk_state: str, pain_level: str, suicide_score: int) -> Dict[str, Any]:
    plan_level = str(memory.get("plan_level", ""))
    urgency = str(memory.get("urgency", ""))
    past_attempt_yes = bool(memory.get("past_attempt_yes") is True)
    family_hit = bool(memory.get("family_suicide") is True)
    event_text = str(memory.get("event_text", ""))
    cl5 = _detect_cl5_from_event(event_text)
    event_categories_hit = cl5["event_categories_hit"]
    event_keywords_hit = cl5["event_keywords_hit"]

    # CL1 통일 기준: risk_state >= S2
    checklist_1_hit = final_risk_state in {"S2", "S3"}
    checklist_2_hit = pain_level in {"중간", "높음"}
    checklist_3_hit = past_attempt_yes
    checklist_4_hit = (plan_level == "C") or (urgency == "오늘/곧바로")
    # CL5는 오직 event_text 기반 판정
    checklist_5_hit = bool(cl5["checklist_5_hit"])
    checklist_6_hit = family_hit

    hit_1_2 = checklist_1_hit or checklist_2_hit
    hit_3_6_count = sum(1 for v in [checklist_3_hit, checklist_4_hit, checklist_5_hit, checklist_6_hit] if v)
    hit_all_6 = all([checklist_1_hit, checklist_2_hit, checklist_3_hit, checklist_4_hit, checklist_5_hit, checklist_6_hit])

    if checklist_4_hit or hit_all_6:
        referral_level = "extreme_crisis"
        referral_notes = [
            "극도의 위기상황: 학생을 절대 혼자 두어선 안 됨",
            "보호자에게 즉시 연락하고 전문가에게 의뢰 필요",
            "전문가 상의 후 필요하다면 입원치료 고려",
        ]
    elif hit_1_2 and hit_3_6_count >= 1:
        referral_level = "needs_specialist_referral"
        referral_notes = ["심층사정평가 및 전문가 의뢰가 필요"]
    elif checklist_1_hit or checklist_2_hit:
        referral_level = "periodic_followup"
        referral_notes = ["주기적 평가와 상담이 고려됨"]
    else:
        referral_level = "none"
        referral_notes = []

    checklist_hits: List[int] = []
    for idx, hit in enumerate(
        [checklist_1_hit, checklist_2_hit, checklist_3_hit, checklist_4_hit, checklist_5_hit, checklist_6_hit],
        start=1,
    ):
        if hit:
            checklist_hits.append(idx)

    evidence = {
        "1": f"risk_state={final_risk_state}",
        "2": f"pain_level={pain_level}",
        "3": f"past_attempt_yes={past_attempt_yes}",
        "4": f"plan_level={plan_level}, urgency={urgency}",
        "5": f"event_categories_hit={event_categories_hit}, event_keywords_hit={event_keywords_hit}",
        "6": f"family_suicide={family_hit}",
    }

    return {
        "checklist_1_hit": checklist_1_hit,
        "checklist_2_hit": checklist_2_hit,
        "checklist_3_hit": checklist_3_hit,
        "checklist_4_hit": checklist_4_hit,
        "checklist_5_hit": checklist_5_hit,
        "checklist_6_hit": checklist_6_hit,
        "checklist_hits": checklist_hits,
        "checklist_hit_any": bool(checklist_hits),
        "event_categories_hit": event_categories_hit,
        "event_keywords_hit": event_keywords_hit,
        "hit_1_2": hit_1_2,
        "hit_3_6_count": hit_3_6_count,
        "hit_all_6": hit_all_6,
        "referral_level": referral_level,
        "referral_notes": referral_notes,
        "checklist_evidence": evidence,
    }


# 역할: 종료 요약용 structured_fields를 조합한다.
def build_structured_fields(
    memory: Dict[str, Any],
    monitoring: Dict[str, Any],
    scoring_breakdown: Dict[str, Any],
) -> Dict[str, Any]:
    final_risk_state = monitoring.get("risk_state", "S0")
    pain_level = str(monitoring.get("정서적_고통_상태", "낮음"))
    suicide_score = int(monitoring.get("자살_신호_점수", 0))

    hits = evaluate_checklist_hits(memory, final_risk_state, pain_level, suicide_score)

    return {
        "event_text": memory.get("event_text", ""),
        "ideation": "Y" if memory.get("ideation") is True else "N" if memory.get("ideation") is False else "",
        "freq": memory.get("freq", ""),
        "plan_level": memory.get("plan_level", ""),
        "urgency": memory.get("urgency", ""),
        "past_attempt_yes": bool(memory.get("past_attempt_yes") is True),
        "past_ideation_yes": bool(memory.get("past_ideation_yes") is True),
        "past_text": memory.get("past_text", ""),
        "past": memory.get("past_category", "none"),
        "family_suicide": "Y" if memory.get("family_suicide") is True else "N" if memory.get("family_suicide") is False else "",
        "suicide_score": monitoring.get("자살_신호_점수", 0),
        "pain_score": monitoring.get("정서적_고통_점수", 0),
        "pain_state": pain_level,
        "final_risk_state": final_risk_state,
        "scoring_rationale": scoring_breakdown,
        "transcript": memory.get("transcript", []),
        **hits,
    }


# 역할: 발동된 트리거 목록을 로그용 문자열로 변환한다.
def _trigger_label(triggers: Dict[str, bool]) -> str:
    active = [k for k, v in triggers.items() if v]
    return ",".join(active) if active else "none"


# 역할: 종료 시 내부 로그용 한 줄 요약을 생성한다.
def build_final_one_liner(structured_fields: Dict[str, Any]) -> str:
    triggers = structured_fields.get("scoring_rationale", {}).get("triggers", {})
    return (
        f"risk_state={structured_fields.get('final_risk_state', 'S0')} | "
        f"suicide={structured_fields.get('suicide_score', 0)} pain={structured_fields.get('pain_score', 0)} | "
        f"triggers={_trigger_label(triggers)} | "
        f"event={str(structured_fields.get('event_text', ''))[:20]} | "
        f"ideation={structured_fields.get('ideation', '')} freq={structured_fields.get('freq', '')} | "
        f"referral={structured_fields.get('referral_level', '')}"
    )


# 역할: 구조화 요약을 자연어 3~5문장으로 변환한다.
def natural_summary_from_structured(structured_fields: Dict[str, Any]) -> str:
    settings = load_settings()
    model = "gemini-2.5-flash-lite"

    prompt = (
        "다음 구조화 정보를 3~5문장으로 자연스럽게 요약해.\n"
        "규칙: 방법/수단/절차 상세 금지, 과장 금지, 한국어 반말.\n"
        f"STRUCTURED_JSON:\n{json.dumps(structured_fields, ensure_ascii=False)}"
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    data = json.dumps(payload).encode("utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            text_out = (
                parsed.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            ).strip()
            if text_out:
                return text_out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2**attempt)
                continue
            if attempt == 2:
                break
            time.sleep(2**attempt)
        except Exception:
            if attempt == 2:
                break
            time.sleep(2**attempt)

    return (
        f"오늘 대화에서 가장 큰 사건은 '{str(structured_fields.get('event_text', ''))[:20]}'였어. "
        f"정서적 고통 점수는 {structured_fields.get('pain_score', 0)}, 자살 신호 점수는 {structured_fields.get('suicide_score', 0)}이야. "
        f"최종 위험 상태는 {structured_fields.get('final_risk_state', 'S0')}로 판단됐어. "
        f"내부 권고 수준은 {structured_fields.get('referral_level', 'none')}로 정리됐어."
    )
