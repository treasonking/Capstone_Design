# 주민센터 공식자료 보강 검증

검증일: 2026-11-02. 기준 커밋: `3627af3d30d8b61005c7d495626f5881670c2049` 이후 이번 변경.
환경: Linux, Python 3.12.14, Node v24.22.1. 별도 가상환경에 `.[dev,perf]` 설치 성공.

## 변경 요약

10개 자료 ID와 기존 검색 키워드를 유지하고 전국 공통 안내 7건과 지역 참고 3건을 구분했다.
정부24·행정안전부 안내를 대조해 대리·온라인 신청, 수수료와 예외, 민원별 증빙 및 추가 확인 범위를 보강했다.
최종 응답의 출처에 적용 범위를 표시하고 보조 근거 URL도 출력 Validator 이전에 합친다.
운영시간·전화·창구 등 특정 센터 정보는 미등록이라고 Provider에 지시한다.

공식 URL과 대조 방식: [자료 출처 검토표](../docs/resident_center_sources.md).
작업 범위 및 후속 구현: [Codex 작업 기록](../docs/codex_resident_center_sources.md).

## 실제 실행

실제 서버 검증 명령:

```bash
/workspace/scratch/1377a8620d88/capstone-review-venv/bin/python -m pytest backend/tests/test_resident_center_agent.py backend/tests/test_resident_center_conversation.py backend/tests/test_user_chat_contract.py backend/tests/test_provider_proxy_integration.py backend/tests/test_sse_proxy_api.py backend/tests/test_proxy_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_ui_routes.py backend/tests/test_demo_ui_contract.py backend/tests/test_providers.py backend/tests/test_llm_service.py backend/tests/test_proxy_e2e.py backend/tests/test_validator_agent.py backend/tests/test_audit_service.py backend/tests/test_audit_integrity.py -q --junitxml=/tmp/resident_sources_results.xml
```

결과: **133 passed, 3 warnings in 11.42s**. 경고는 기존 Starlette TestClient의 httpx 사용과 FastAPI startup hook deprecation이다.
이 수치는 위 15개 파일의 관련 회귀이며 전체 저장소 테스트 수가 아니다.

```bash
node --test frontend/demo_async.test.js
python -m json.tool backend/app/data/resident_center_services.json
git diff --check
git status --short --branch
```

화면 검사 **32 passed, 0 failed**. JSON 파싱과 diff 공백 검사 통과.
서버 검사에 화면 테스트 실행 래퍼가 포함되므로 133과 32를 합산해 독립 테스트 수로 표현하지 않는다.
JUnit과 화면 원출력은 실행 환경 `/tmp`의 임시 증거이며 배포 데이터가 아니다.

## 증거 범위

| 주장 | 근거 | 상태와 한계 |
|---|---|---|
| 변경 자료가 인증된 채팅으로 전달되고 출처 범위가 반환됨 | 주민센터 통합 테스트 | Confirmed — Provider 응답은 합성 |
| 인감 온라인 제한에 보조 근거가 전달·표시됨 | 추가 인증 API 회귀 | Confirmed — 실제 모델의 제한 준수는 미검증 |
| 이력 PII와 공격 입력, 위험 출력에 기존 검사가 유지됨 | 대화·Provider·Validator·감사 로그 회귀 | Confirmed — 내부 사례 범위, 일부 시나리오는 경량 탐지기 비활성화 |
| 10개 자료의 ID·범위·공식 HTTPS 출처·확인일·한계가 존재함 | 자료 추적성 검사 | Confirmed — 내용의 법적 정확성 검사는 아님 |
| 화면 이력·취소·재시도 동작 유지 | Node 화면 계약 검사 | Confirmed — 실제 브라우저 클릭 검사는 아님 |
| 최신 법령 전체와 정확히 일치함 | 이번 작업에 해당 검증 없음 | Not verified |
| 실제 LLM이 정확한 안내를 생성함 | 이번 작업에 실 API 호출 없음 | Not verified |

## 실행하지 않은 항목과 남은 리스크

- 유료 OpenAI 호출·실제 민원 접수·발급·행정망 조회·실시간 법령 API를 실행하지 않았다.
- 정부24는 공식 검색 추출문 대조이며 전체 원문 검토와 구분한다. 지역·상황별 예외와 변경 가능성은 남는다.
- 특정 행복 주민센터의 소재지가 미확정이므로 운영정보는 추가하지 않았다. 실제 모델이 운영정보를 추측하지 않는지 검증이 필요하다.
- 키워드 검색, 비신뢰 대화 이력, 간접 인젝션·환각·근거 불일치 위험은 그대로다. 지침과 출처 표시는 이를 제거하는 기계적 보장이 아니다.
- PII·인젝션 탐지 규칙 및 탐지 benchmark 데이터는 변경하지 않았다. 이번 민원자료 변경은 위 통합 회귀로 확인했으며 기존 외부 성능 평가를 다시 측정한 결과가 아니다.
- 기존 PQC는 ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 구조이며 변경하지 않았다.

## 다음 권장 작업

대상 센터의 공식 운영정보를 확인한 뒤 별도로 등록한다. 승인된 모델 환경에서 정상·대리·온라인 제한·
미수록 업무·타지역·운영시간 질문을 실행하고, 답변별 자료 ID 일치·과도한 확정·누락을 따로 평가한다.
