from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import src.agent as agent_mod
from src.agent_session import AgentSession


def _patch_offline() -> None:
    agent_mod.generate_reply = lambda **kwargs: "네 얘기 잘 들었어."
    agent_mod.detect_sentiment = lambda text: {"label": "POSITIVE" if "좋" in text else "NEGATIVE", "confidence": 0.9}
    agent_mod.natural_summary_from_structured = lambda sf: "테스트 요약"


TEST_CASES: List[Dict[str, Any]] = [
    {"id": "TC01", "inputs": ["우울했어", "친구들이 날 괴롭혀", "아니 그런 생각은 안 들어"], "expects": {"final_risk_in": ["S0", "S1"], "end_reason": "resolved"}},
    {"id": "TC02", "inputs": ["우울했어", "왕따당했어", "응 죽고 싶더라", "가끔", "막연한 생각이야", "지금 당장은 아니야", "시도한 적은 없어", "아니오"], "expects": {"urgency": "당장아님", "risk": "S1", "suicide": 45, "end_reason": "questionnaire_complete"}},
    {"id": "TC03", "inputs": ["힘들었어", "왕따당했어", "응 죽고 싶어", "자주", "구체적인 계획이 있어", "지금 당장은 아니야", "시도한 적은 없어", "아니오"], "expects": {"final_risk": "S3", "trigger_true": ["TR2"]}},
    {"id": "TC04", "inputs": ["우울했어", "가족 때문에 너무 힘들어", "응", "가끔", "막연", "오늘/지금 당장일 것 같아", "시도한 적은 없어", "아니오"], "expects": {"final_risk": "S3", "trigger_true": ["TR1"]}},
    {"id": "TC05", "inputs": ["우울했어", "왕따야", "응", "자주", "구체", "지금은 아니야", "시도한 적 있어", "아니오"], "expects": {"urgency": "당장아님", "trigger_false": ["TR1"], "trigger_true": ["TR2"], "final_risk": "S3"}},
    {"id": "TC06", "inputs": ["  우 울 했 어  ", "학교에서\t애들이\u200B나를  괴롭히고 \u00A0왕따시켰어", "어  요 즘   살기  싫어", "가끔", "막연", "지금 당장은 아니야", "시도한 적은 없어", "아니오"], "expects": {"normalized_event": True}},
    {"id": "TC07", "inputs": ["우울했어", "왕따당했어", "응", "자주", "구체적인 계획을 세워본 적이 있어", "지금 당장은 아니야", "시도한 적은 없어", "아니오"], "expects": {"plan_level": "C"}},
    {"id": "TC08", "inputs": ["힘들어", "괴롭힘", "응", "가끔 생각나", "막연", "지금 당장은 아니야", "없음", "아니오"], "expects": {"freq": "가끔"}},
    {"id": "TC09", "inputs": ["우울", "왕따", "응", "가끔", "막연", "지금 당장은 아니야", "생각은 해봤는데 시도는 안 했어", "아니오"], "expects": {"past_ideation_yes": True, "past_attempt_yes": False}},
    {"id": "TC10", "inputs": ["오늘 너무 좋았어", "친구랑 웃긴 일 있었어"], "expects": {"end_reason": "user_positive_close"}},
    {"id": "TC11", "inputs": ["우울", "왕따", "응", "가끔", "막연", "지금 당장은 아니야", "없음", "아니오"], "expects": {"risk": "S1", "suicide": 45, "end_reason_not": ["resolved"]}},
    {"id": "TC12", "inputs": ["우울", "왕따", "응", "자주", "구체", "지금 당장은 아니야", "시도한 적 있어", "예"], "expects": {"final_risk": "S3", "checklist_6_hit": True, "end_reason": "questionnaire_complete"}},
]


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _to_print_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        out.append(
            {
                "turn": idx,
                "question_type": row.get("행동", {}).get("질문_유형", ""),
                "question": row.get("기억", {}).get("마지막_qna", {}).get("q", ""),
                "user_answer": row.get("기억", {}).get("마지막_qna", {}).get("a", ""),
                "assistant": row.get("답변", ""),
                "compact_debug": row.get("compact_debug", {}),
            }
        )
    return out


def _assert_case(case: Dict[str, Any], turns: List[Dict[str, Any]]) -> Tuple[bool, List[str], Dict[str, Any]]:
    last = turns[-1]
    end_reason = last.get("대화제어", {}).get("종료_이유", "none")
    summary = (last.get("대화제어", {}).get("summary_if_end", {}) or {})
    sf = summary.get("structured_fields", {}) if isinstance(summary, dict) else {}
    monitoring = last.get("모니터링", {})
    risk = sf.get("final_risk_state", monitoring.get("risk_state", "S0"))
    suicide = sf.get("suicide_score", monitoring.get("자살_신호_점수", 0))
    pain = sf.get("pain_score", monitoring.get("정서적_고통_점수", 0))
    urgency = sf.get("urgency", "")
    triggers = sf.get("scoring_rationale", {}).get("triggers", {})
    expects = case["expects"]
    errors: List[str] = []

    # llm checklist 출력 금지
    if isinstance(sf, dict) and "llm_checklist_summary" in sf:
        errors.append("llm_checklist_summary should not exist")

    q_types = [t.get("행동", {}).get("질문_유형", "") for t in turns]
    if q_types.count("Q_FAMILY_SUICIDE") > 1:
        errors.append("Q_FAMILY_SUICIDE should appear at most once")

    if "final_risk" in expects and risk != expects["final_risk"]:
        errors.append(f"expected final_risk={expects['final_risk']} got {risk}")
    if "final_risk_in" in expects and risk not in expects["final_risk_in"]:
        errors.append(f"expected final_risk in {expects['final_risk_in']} got {risk}")
    if "risk" in expects and risk != expects["risk"]:
        errors.append(f"expected risk={expects['risk']} got {risk}")
    if "suicide" in expects and int(suicide) != int(expects["suicide"]):
        errors.append(f"expected suicide={expects['suicide']} got {suicide}")
    if "urgency" in expects and urgency != expects["urgency"]:
        errors.append(f"expected urgency={expects['urgency']} got {urgency}")
    if "plan_level" in expects and sf.get("plan_level") != expects["plan_level"]:
        errors.append(f"expected plan_level={expects['plan_level']} got {sf.get('plan_level')}")
    if "freq" in expects and sf.get("freq") != expects["freq"]:
        errors.append(f"expected freq={expects['freq']} got {sf.get('freq')}")
    if "past_ideation_yes" in expects and bool(sf.get("past_ideation_yes")) != expects["past_ideation_yes"]:
        errors.append(f"expected past_ideation_yes={expects['past_ideation_yes']} got {sf.get('past_ideation_yes')}")
    if "past_attempt_yes" in expects and bool(sf.get("past_attempt_yes")) != expects["past_attempt_yes"]:
        errors.append(f"expected past_attempt_yes={expects['past_attempt_yes']} got {sf.get('past_attempt_yes')}")
    if "checklist_6_hit" in expects and bool(sf.get("checklist_6_hit")) != expects["checklist_6_hit"]:
        errors.append(f"expected checklist_6_hit={expects['checklist_6_hit']} got {sf.get('checklist_6_hit')}")

    for k in expects.get("trigger_true", []):
        if not bool(triggers.get(k, False)):
            errors.append(f"expected {k}=true got false")
    for k in expects.get("trigger_false", []):
        if bool(triggers.get(k, False)):
            errors.append(f"expected {k}=false got true")

    if "end_reason" in expects and end_reason != expects["end_reason"]:
        errors.append(f"expected end_reason={expects['end_reason']} got {end_reason}")
    for bad in expects.get("end_reason_not", []):
        if end_reason == bad:
            errors.append(f"expected end_reason != {bad} got {end_reason}")

    if expects.get("normalized_event"):
        event_text = str(sf.get("event_text", ""))
        for token in ["\t", "\u200B", "\u00A0", "  "]:
            if token in event_text:
                errors.append(f"event_text contains forbidden token {repr(token)}")

    meta = {
        "risk": risk,
        "suicide": suicide,
        "pain": pain,
        "urgency": urgency or "none",
        "triggers": ",".join([k for k, v in triggers.items() if v]) or "none",
        "end_reason": end_reason,
    }
    return len(errors) == 0, errors, meta


def run_case(case: Dict[str, Any], verbose: bool, save_jsonl: bool, save_print: bool) -> bool:
    session = AgentSession()
    rows: List[Dict[str, Any]] = [session.start_turn()]
    for user_text in case["inputs"]:
        out = session.process_user_text(user_text)
        rows.append(out)
        if out.get("대화제어", {}).get("종료"):
            break

    target_rows = rows[1:] if len(rows) > 1 else rows
    ok, errors, meta = _assert_case(case, target_rows)

    if save_jsonl:
        _write_jsonl(Path("outputs/tests") / f"{case['id']}.jsonl", rows)
    if save_print:
        _write_jsonl(Path("outputs/test_print") / f"{case['id']}.jsonl", _to_print_rows(rows))

    if ok:
        print(
            f"[PASS] {case['id']} risk={meta['risk']} suicide={meta['suicide']} pain={meta['pain']} "
            f"urgency={meta['urgency']} triggers={meta['triggers']} end_reason={meta['end_reason']}"
        )
        if verbose:
            final_sf = (rows[-1].get("대화제어", {}).get("summary_if_end", {}) or {}).get("structured_fields", {})
            print(
                json.dumps(
                    {
                        "transcript": final_sf.get("transcript", []),
                        "scoring_rationale": final_sf.get("scoring_rationale", {}),
                        "checklist": {
                            "checklist_1_hit": final_sf.get("checklist_1_hit"),
                            "checklist_5_hit": final_sf.get("checklist_5_hit"),
                            "event_categories_hit": final_sf.get("event_categories_hit", []),
                            "event_keywords_hit": final_sf.get("event_keywords_hit", []),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return True

    print(
        f"[FAIL] {case['id']} {' | '.join(errors)} | "
        f"last_risk={meta['risk']} suicide={meta['suicide']} pain={meta['pain']} end_reason={meta['end_reason']}"
    )
    if verbose:
        print(json.dumps(rows[-1], ensure_ascii=False, indent=2))
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, help="단일 케이스 실행 (예: TC02)")
    parser.add_argument("--all", action="store_true", help="전체 케이스 실행")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save-jsonl", action="store_true", default=True)
    parser.add_argument("--no-save-jsonl", action="store_true")
    parser.add_argument("--save-print", action="store_true", default=True)
    parser.add_argument("--no-save-print", action="store_true")
    args = parser.parse_args()

    save_jsonl = args.save_jsonl and not args.no_save_jsonl
    save_print = args.save_print and not args.no_save_print
    _patch_offline()

    if args.case:
        selected = [c for c in TEST_CASES if c["id"] == args.case]
    else:
        selected = TEST_CASES if args.all or not args.case else []
    if not selected:
        raise SystemExit("No test cases selected.")

    total = len(selected)
    passed = 0
    for c in selected:
        if run_case(c, verbose=args.verbose, save_jsonl=save_jsonl, save_print=save_print):
            passed += 1
    failed = total - passed
    print(f"TOTAL={total} PASS={passed} FAIL={failed}")
    if save_print:
        print("print logs: outputs/test_print/TCxx.jsonl")


if __name__ == "__main__":
    main()
