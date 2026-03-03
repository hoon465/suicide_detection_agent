from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agent_session import AgentSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _append(path: Path, obj) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _print_turn_for_user(result) -> None:
    answer = str(result.get("답변", "")).strip()
    if answer:
        print(answer)

    if bool(result.get("대화제어", {}).get("종료", False)):
        return

    next_question = str(result.get("행동", {}).get("다음_질문", "")).strip()
    if next_question:
        print(f"\n{next_question}")


def _print_closing(result) -> None:
    if result.get("대화제어", {}).get("종료"):
        summary = (
            result.get("대화제어", {})
            .get("summary_if_end", {})
            .get("natural_summary", "")
        )
        if summary:
            print("\n[대화 요약]")
            print(summary)
        print("오늘 이야기해줘서 고마워. 필요하면 언제든 다시 이어가자.")


# 역할: CLI 인자를 받아 테스트 러너 전체 흐름을 실행한다.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--append", action="store_true", help="기존 transcript 파일에 이어쓰기")
    args = parser.parse_args()

    out_path = PROJECT_ROOT / "outputs" / "transcript.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not args.append:
        out_path.write_text("", encoding="utf-8")
    print(f"[저장경로] {out_path}")

    session = AgentSession()

    # start turn (AI starts)
    first = session.start_turn()
    _append(out_path, first)
    print(first["행동"]["다음_질문"])

    if args.demo:
        demo_inputs = [
            "우울했어",
            "학교에서 애들이 나를 괴롭히고 왕따 시켰어",
            "응 요즘 살기 싫어",
            "자주",
            "구체적인 계획 세워본 적 있어",
            "지금 당장은 아니야",
            "시도한 적 있어",
            "아니",
        ]
        for user_text in demo_inputs:
            print(f"you> {user_text}")
            result = session.process_user_text(user_text)
            _append(out_path, result)
            _print_turn_for_user(result)

            # verification log
            monitor = result.get("모니터링", {})
            summary = result.get("대화제어", {}).get("summary_if_end")
            if summary:
                sf = summary.get("structured_fields", {})
                triggers = sf.get("scoring_rationale", {}).get("triggers", {})
                print(
                    "[검증] urgency=", sf.get("urgency", ""),
                    "TR1=", triggers.get("TR1", False),
                    "pain=", sf.get("pain_score", 0),
                    "end_reason=", result.get("대화제어", {}).get("종료_이유", "none"),
                )
            else:
                print(
                    "[검증] risk=", monitor.get("risk_state", ""),
                    "pain=", monitor.get("정서적_고통_점수", 0),
                    "suicide=", monitor.get("자살_신호_점수", 0),
                )
            if result.get("대화제어", {}).get("종료"):
                _print_closing(result)
                break
        return

    while True:
        user_text = input("you> ")
        if not user_text:
            continue

        result = session.process_user_text(user_text)
        _append(out_path, result)
        _print_turn_for_user(result)

        if result.get("대화제어", {}).get("종료"):
            _print_closing(result)
            break


if __name__ == "__main__":
    main()
