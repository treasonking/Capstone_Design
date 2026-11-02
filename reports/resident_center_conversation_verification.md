# 대화 연결·민원 확대·정상 및 공격 질문 통합 검증

검증일: 2026-11-02. 이전 3개 업무·단일 질문 단계 이후의 확장 기록이다.

## 구현 결과

1. 기존 `/app` 채팅에서 성공한 같은 안내 유형의 최근 6개 질문·답변 쌍을 연결했다. 실패·차단 답변은 재사용하지 않는다.
   새 대화·로그아웃·화면 이탈·새로고침 시 브라우저 메모리 이력이 초기화된다. 서버 대화 DB는 만들지 않았다.
2. `history` 역할·항목수·글자수·전체 크기를 서버에서 제한한다. 이력을 포함한 입력 전체를 preflight와 chat에서 각각 재검사한다.
   정책 차단이면 검색·Provider 호출을 생략하며, 허용된 요청은 이력의 개인정보까지 마스킹해 Provider에 전달한다.
   클라이언트 제공 과거 답변은 실제 시스템/개발자/assistant API 메시지로 승격하지 않는다.
3. 공개 안내를 전입신고, 등초본, 인감증명, 주민등록증 재발급, 가족관계증명, 출생신고, 사망신고,
   확정일자, 본인서명사실확인서, 대형폐기물의 **10개 업무**로 확대했다. 공식 원문과 확인일·지역·한계를 각 자료에 기록했다.
4. 후속 표현이면 최근 사용자 업무를 참고하고, 새 업무가 명시되면 현재 질문의 업무를 우선 검색한다.

## 질문 시나리오

`evaluation/datasets/resident_center_scenarios.json`에는 합성 질문 **25건**을 넣었다.

| 구분 | 건수 | 검증 내용 |
|---|---:|---|
| 정상 민원 | 10 | 업무별 공개자료 선택·출처 반환 |
| 대화 연결 | 4 | 대리 방문·수수료·지역 답변 후속 질문, 업무 전환 |
| 미수록 업무 | 2 | 과거 업무를 근거로 잘못 확정하지 않고 자료 없음 표시 |
| 개인정보 | 4 | 현재 질문·과거 사용자·과거 답변·모델 출력의 마스킹 |
| 공격 | 5 | 한영 인젝션, 과거 사용자/답변에 숨긴 공격, 위험한 모델 출력 차단 |

여기에 잘못된 역할/순서/크기 등 이력 계약 6건과 SSE 이력 공격 1건을 더해 신규 서버 검증은 32건이다.
검증은 인증된 FastAPI 경로를 사용하며 정책 엔진·탐지·마스킹·Validator·감사 로그는 실제 코드를 실행했다.
Provider 응답만 합성 응답으로 대체했고, 결정적인 재현을 위해 신규 시나리오에서는 `ENABLE_MODEL_DETECTOR=false`를 설정했다.
따라서 경량 모델을 포함한 Hybrid 성능이나 실제 LLM 답변 품질 측정으로 해석하지 않는다.

## 실행 결과

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_resident_center_conversation.py backend/tests/test_resident_center_agent.py backend/tests/test_user_chat_contract.py backend/tests/test_provider_proxy_integration.py backend/tests/test_sse_proxy_api.py backend/tests/test_proxy_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_ui_routes.py backend/tests/test_demo_ui_contract.py backend/tests/test_providers.py backend/tests/test_llm_service.py backend/tests/test_proxy_e2e.py backend/tests/test_validator_agent.py backend/tests/test_audit_service.py backend/tests/test_audit_integrity.py -q --junitxml=reports/resident_center_conversation_results.xml
```

**128 passed, 3 warnings in 19.59s**. 결과 원본은 `reports/resident_center_conversation_results.xml`이다.
이는 신규 32건을 포함한 관련 서버/계약 회귀 검증이며 전체 저장소 테스트 결과는 아니다.
경고 3건은 기존 FastAPI startup hook·Starlette httpx TestClient의 deprecation이다.

```powershell
node --test frontend/demo_async.test.js
git diff --check
```

화면 동작 검증은 **32 passed, 0 failed**. 성공한 대화만 전달, 6쌍 제한, 초기화, 유형 전환 시 이력 분리,
원래 유형·질문·이력으로 재시도, 오류·취소·오래된 응답 무시 등을 확인했다.
서버 검증에도 화면 테스트 실행 래퍼가 포함되므로 위 수치를 서로 더해 독립 테스트 수로 표현하지 않는다.
`git diff --check` 통과. 이번 단계의 최종 검증에는 남은 실패가 없다.

## 남은 제한

- 실제 OpenAI 키·모델 환경변수가 없어 유료 실 API 호출은 실행하지 않았다. 생성 답변의 정확성·후속 질문 이해·환각 억제는 미검증이다.
- 25건은 설계한 내부 회귀 사례다. 일반적인 인젝션 방어율·탐지 성능을 보장하지 않는다. 기존 외부 벤치마크 수치는 변경하지 않았다.
- 탐지기 자체나 정책 규칙은 변경하지 않았다. 신규 대화·질문 데이터셋은 위 통합 검사로 검증했으며 기존 탐지 성능 평가를 다시 측정한 결과는 아니다.
- 과거 답변을 클라이언트가 위조할 수 있고 키워드 기반 주제 추론에는 누락·오분류가 남는다. 모든 문맥 공격과 RAG 간접 인젝션 방어를 보장하지 않는다.
- 공개자료는 수동 요약 스냅샷이다. 현행 법령 전체 대조·자동 갱신·전국 지역차 검증·행정망·실시간 법령 API·실제 접수/발급은 미완료다.
- Validator는 개인정보·정책 검사이며 행정 안내의 법적 정확성이나 근거 일치를 자동 검증하지 않는다.
- PQC는 기존 ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조 그대로다.
