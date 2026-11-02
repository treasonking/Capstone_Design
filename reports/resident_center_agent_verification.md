# 주민센터 안내 통합 검증 · 2026-11-02

이 문서는 최초 단일 질문 시제품 통합 시점의 기록이다. 대화 연결·10개 업무 확장 이후 결과는
[대화·민원 확대 통합 검증](resident_center_conversation_verification.md)을 기준으로 확인한다.

## 변경 범위

- 기존 사용자 채팅에 주민센터 안내/일반 질문 선택을 추가했다.
- `assistant=resident_center` 요청은 기존 입력 검사와 Provider 직전 마스킹 후 공개자료를 검색한다.
- 검색자료와 전문 역할 지침을 기존 OpenAI Provider의 시스템 지침에 전달한다.
- 검색 출처를 답변에 추가한 후 기존 Validator를 실행한다. 차단 시 출처를 포함한 답변 전체를 반환하지 않는다.
- 일반/관리자 계약, 감사 로그의 원문 비저장 원칙, SSE 버퍼링 후 출력 검증을 유지한다.

## 검증 명령과 실제 결과

프로젝트 전용 `.venv`에 `pip install -e '.[dev]'`로 기존 선언 의존성을 설치했다.

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_resident_center_agent.py backend/tests/test_user_chat_contract.py backend/tests/test_provider_proxy_integration.py backend/tests/test_sse_proxy_api.py backend/tests/test_proxy_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_ui_routes.py backend/tests/test_demo_ui_contract.py backend/tests/test_providers.py backend/tests/test_llm_service.py -q
```

결과: **77 passed, 3 warnings**. 경고는 FastAPI startup hook과 Starlette의 기존 httpx TestClient 사용에 대한 deprecation이다.
이는 새 에이전트와 관련 모듈의 회귀 검증이며 전체 프로젝트 테스트나 탐지 성능 평가 결과가 아니다.
새 테스트에서는 자료 검색, 마스킹 후 Provider 전달, preflight 무호출, 차단 시 검색 생략,
일반 경로 호환, 알 수 없는 유형 거부, 근거 없는 업무, 출력 차단, SSE 경로, 감사 로그 원문 비저장을 확인했다.

```powershell
node --test frontend/demo_async.test.js
git diff --check
```

화면 동작 검증: **30 passed, 0 failed**. 안내 유형 선택과 실패 후 원래 유형으로 재시도하는 동작을 기존 테스트에 포함했다.
`git diff --check` 통과.

## 초기 실패와 해결

- 제한된 Windows 실행 환경에서 서버 테스트가 asyncio의 로컬 socketpair 초기화에 멈췄다. 중단 후 일반 실행 환경에서 재실행해 통과했다.
- 시스템 Python의 확대 검증은 `openai` 미설치로 수집에 실패했다. 전용 가상환경에 프로젝트 의존성을 설치한 후 위 77건이 통과했다.
- 화면 검증은 새 요청 필드의 기존 기대값을 갱신하기 전 실패했다. 기대값을 갱신하고 유형 선택·재시도 검증을 추가한 후 30건이 통과했다.
- 화면의 기존 10ms timeout 검증 중 한 번은 두 번째 요청 전 timeout이 발생했다. 재실행에서는 통과했지만 해당 테스트의 실행 부하 민감성은 남아 있다.

## 미검증과 제한

- 실제 OpenAI 키가 설정되지 않아 유료 실 API 호출·모델 답변 품질은 검증하지 않았다. Provider 테스트는 대체 응답 기반이다.
- 공개자료는 한 지역 페이지의 수동 요약 3건이다. 현행 법령 대조, 자료 자동 갱신, 전국 지자체 차이 검증은 미완료다.
- 기초 RAG 검색이며 모델 재학습·자율 도구 호출·이전 대화 전달은 없다.
- 행정망·실시간 법령 API·접수·발급·개인별 자격 조회는 미구현이다.
- Validator는 출력 안전성 검사이며 행정 안내 정확성/출처 일치의 자동 사실검증 기능이 아니다.
