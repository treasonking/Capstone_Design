# 주민센터 자료 확대 검증 보고서

검증일: 2026-11-03. 선행 PR #15 커밋: `015d9233aadaeb6cdd91ffec3fb8c0d6a589a078`.
로컬 기준 커밋 `fe7bbcc`는 해당 원격 커밋과 동일한 소스 트리다. 별도 worktree에서 작업하여 기존 checkout의 다른 변경은 보존했다.
환경: Linux, Python 3.12.14, Node v24.22.1. 별도 가상환경에 `.[dev,perf]` 설치 성공.

## 변경 결과

기존 10개에서 **30개 업무 요약자료**로 확대했다. 전국 제도 안내 26건, 지역 참고자료 4건이며 새 업무는 20종이다.
공식 출처와 요약·예외·추가 확인 질문은 [자료 확대 기록](../docs/resident_center_expansion.md)에 정리했다.
같은 원문을 분할해 개수만 부풀린 상세 문서 80건이나 전국 모든 업무를 포괄하는 데이터베이스로 표현하지 않는다.

## 최초 검사와 실패

```bash
/workspace/scratch/1377a8620d88/expansion-venv/bin/python -m pytest backend/tests/test_resident_center_expansion.py backend/tests/test_resident_center_agent.py backend/tests/test_resident_center_conversation.py -q --junitxml=/tmp/resident_expansion_focused.xml
```

최초 결과: **1 failed, 145 passed, 3 warnings in 11.39s**.
한국어 직접 공격 사례는 올바르게 BLOCK되었지만, 입력 문장이 `input.prompt_injection.matched_terms` 안에 저장되어 로그 비저장 단언이 실패했다.
이는 자료 검색 오류가 아니라 기존 감사 로그의 문자열 저장 경로였다. 실패 사례나 기대 action을 삭제·완화하지 않았다.
로그 저장 전 재귀 정리에서 `matched_terms`와 `matched_text`를 제외하고 별도 중첩 필드 회귀를 추가했다.

## 최종 실제 실행

```bash
/workspace/scratch/1377a8620d88/expansion-venv/bin/python -m pytest backend/tests/test_resident_center_expansion.py backend/tests/test_resident_center_agent.py backend/tests/test_resident_center_conversation.py backend/tests/test_user_chat_contract.py backend/tests/test_provider_proxy_integration.py backend/tests/test_sse_proxy_api.py backend/tests/test_proxy_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_ui_routes.py backend/tests/test_demo_ui_contract.py backend/tests/test_providers.py backend/tests/test_llm_service.py backend/tests/test_proxy_e2e.py backend/tests/test_validator_agent.py backend/tests/test_audit_service.py backend/tests/test_audit_integrity.py -q --junitxml=/tmp/resident_expansion_final.xml
```

**234 passed, 3 warnings in 19.98s**. 경고는 기존 Starlette TestClient의 httpx 사용과 FastAPI startup hook deprecation이다.
이 수치는 위 관련 16개 파일의 회귀 결과이며 저장소 전체 테스트 결과는 아니다.

```bash
node --test frontend/demo_async.test.js
python -m json.tool backend/app/data/resident_center_services.json
python -m json.tool evaluation/datasets/resident_center_expansion_scenarios.json
git diff --check
git status --short --branch
```

화면 계약 **32 passed, 0 failed**. 두 JSON 파싱·diff 공백 검사 통과.
서버 회귀에 화면 래퍼가 포함되므로 234와 32를 합산해 독립 테스트 수로 표현하지 않는다.
실행 원출력과 JUnit은 `/tmp`에 보관한 임시 증거이며 배포 자료가 아니다.

## 신규 100개 질문의 검사 경계

| 구분 | 건수 | 실제 검사 | 상태 |
|---|---:|---|---|
| 업무별 2개 표현 | 60 | 기대 문서 첫 순위, 인증 API의 Provider 문맥과 최종 출처 포함 | Confirmed |
| 신규 업무 후속 | 20 | 업무명 없는 질문에 최근 사용자 업무 활용 | Confirmed |
| 미수록 업무 | 10 | 검색 결과 없음, 빈 문맥, 자료 없음 표시 | Confirmed |
| 개인정보·공격·위험 출력 | 10 | 입력·이력·합성 출력의 MASK/BLOCK과 로그 비저장 | Confirmed |

신규 검사에서는 `ENABLE_MODEL_DETECTOR=false`로 경량 탐지기를 비활성화하고 Provider 응답만 합성 값으로 대체했다.
입력 검사·정책·egress 마스킹·출력 Validator·감사 로그는 실제 코드를 실행했다. 직접 검색 단위 함수만 호출한 결과로 설명하지 않는다.
기존 25개 민원 시나리오·이력 계약·SSE·Provider·감사 서명 관련 회귀도 최종 명령에 포함했다.

## 미검증 항목과 리스크

- 실제 유료 LLM 호출·답변 정확성·근거 일치·환각률은 Not verified다. 합성 Provider 통과를 실제 답변 품질로 주장하지 않는다.
- 100개는 설계한 내부 사례다. 독립 holdout 또는 외부 benchmark가 아니며 일반 검색 정확도·공격 방어율로 일반화하지 않는다.
- 탐지 규칙과 외부 평가 데이터는 변경하지 않았다. 자료 확대와 로그 정리를 위 회귀로 검증했으며 기존 탐지 성능 평가 수치를 재측정한 결과가 아니다.
- 공식 자료는 원문 해당 구간 또는 검색 추출문 대조이며 모든 현행 법령·지역 예외를 확인한 것은 아니다. 확인일은 시행일·최신성 보증이 아니다.
- 특정 행복 주민센터의 운영정보·전국의 지역별 복지·수수료·서식 차이는 미확인이다. 실시간 법령·행정망·실제 접수·발급·재산조회는 구현하지 않았다.
- 로그 수정은 알려진 두 필드의 저장을 막는 범위다. 이미 저장된 로그를 정리하지 않았으며 모든 자유형 메타데이터 필드에 대한 완전한 유출 방지를 증명하지 않는다.
- 키워드·후속 표현 기반 검색, 비신뢰 이력 위조, 간접 인젝션과 모델의 지침 불이행 위험은 남는다.

## 다음 작업

PR 반영 후 서버를 재시작해 JSON 캐시를 갱신한다. 승인된 실제 모델 환경에서 독립 질문을 추가해 답변 근거·예외 누락·불필요한 개인정보 요청을 별도로 평가한다.
