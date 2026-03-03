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

- 질문은 `src/question_bank.py`의 고정 질문 세트를 사용합니다.
- `Q_START` 감정 분기와 `Q_IDEATION` 판정은 LLM(Gemini) 우선으로 처리합니다.
- 점수 계산은 규칙 기반 가중치(`suicide_score`, `pain_score`, TR1/TR2)로 수행합니다.
- CLI 화면에는 대화 텍스트만 출력하고, 턴별 JSON은 파일에 저장합니다.
- 종료 시 `summary_if_end`에 구조화 필드와 자연어 요약을 생성합니다.

## src 파일 설명 (간략)

- `src/agent.py`: 턴 단위 상태 전이와 전체 대화 로직
- `src/agent_session.py`: 세션 래퍼(시작 턴/사용자 입력 처리)
- `src/config.py`: `.env`/환경변수 로딩
- `src/gemini_chat.py`: Gemini 공감 응답 생성
- `src/sentiment_detector.py`: 시작 감정 판정 + 현재 시점 ideation 판정
- `src/scoring.py`: 점수 계산, 파싱, risk state 판정
- `src/summarizer.py`: 종료 요약/체크리스트/구조화 필드 생성
- `src/question_bank.py`: 질문 키-문장 매핑
- `src/memory.py`: 대화 메모리 초기화/저장 유틸
- `src/schemas.py`: 턴 기본 JSON 스키마
- `src/utils.py`: 입력 정규화 유틸
- `src/__init__.py`: 외부 노출 엔트리(`run_turn`, `init_state`, `AgentSession`)

## 테스트 실행

전체 테스트(기본: 실제 LLM 호출):
```bash
python3 -m scripts.run_tests --all
```

단일 케이스:
```bash
python3 -m scripts.run_tests --case TC02
```

오프라인 스텁 테스트(LLM 호출 없음):
```bash
python3 -m scripts.run_tests --all --offline
```

테스트 로그:
- full: `outputs/tests/TCxx.jsonl`
- compact: `outputs/test_print/TCxx.jsonl`
