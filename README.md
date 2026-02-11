# Suicide Detection Agent

질문 기반 대화를 통해 정서적 고통/자살 신호를 점수화하고, 대화 종료 시 요약과 구조화 결과를 남기는 에이전트입니다.

## 빠른 실행

1. 의존성 설치
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정 (`.env`)
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

3. CLI 실행
```bash
python3 -m scripts.run_cli
```

4. 데모 실행
```bash
python3 -m scripts.run_cli --demo
```

로그는 `outputs/transcript.jsonl`에 저장됩니다.

## 동작 방식 요약

- 질문은 `src/question_bank.py`의 고정 질문 세트를 사용
- 리스크 판정은 규칙 기반 점수(`suicide_score`, TR1/TR2 트리거)로 수행
- 각 턴 결과는 JSON 형태로 출력/저장
- 종료 시 `summary_if_end`에 구조화 필드와 자연어 요약을 생성

## src 파일 설명 (간략)

- `src/agent.py`: 턴 단위 상태 전이와 전체 대화 로직
- `src/agent_session.py`: 세션 래퍼(시작 턴/사용자 입력 처리)
- `src/config.py`: `.env`/환경변수 로딩
- `src/gemini_chat.py`: Gemini 공감 응답 생성
- `src/sentiment_detector.py`: 간단 감정 분류(POSITIVE/NEGATIVE/NEUTRAL)
- `src/signal_detector.py`: 자살 위험 단서 감지(JSON 출력)
- `src/scoring.py`: 점수 계산, 파싱, risk state 판정
- `src/summarizer.py`: 종료 요약/체크리스트/구조화 필드 생성
- `src/question_bank.py`: 질문 키-문장 매핑
- `src/memory.py`: 대화 메모리 초기화/저장 유틸
- `src/schemas.py`: 턴 기본 JSON 스키마
- `src/utils.py`: 입력 정규화 유틸
- `src/state_eval.py`: 상태 평가 보조 로직(레거시/보조)
- `src/checklist.py`: 체크리스트 평가 보조 모듈
- `src/__init__.py`: 외부 노출 엔트리(`run_turn`, `init_state`, `AgentSession`)

## 테스트 실행

전체 테스트:
```bash
python3 -m scripts.run_tests --all
```

단일 케이스:
```bash
python3 -m scripts.run_tests --case TC02
```
