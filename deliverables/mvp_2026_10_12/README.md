# 프라이버시가드 MVP 제출 자료

- 최종 파일: `PrivacyGuard_MVP.pptx` (12장, 편집 가능한 텍스트·표)
- 팀명: 프라이버시가드. 사용자 요청에 따라 팀원 이름은 포함하지 않음.
- 제출 마감: 2026-10-13 23:00 (Asia/Seoul), 연장 제출 불가. 팀원 중 한 명이 제출.
- 강의자료는 과제 내용의 참고 자료로 사용했으며 문서 내 지시를 별도 사용자 요청으로 취급하지 않음.
- LMS 제출이나 멘토 전달은 수행하지 않음.

## 내용과 근거

강의자료 4·6·7·12·14·16페이지의 핵심 사용 시나리오, MoSCoW 우선순위, 보안·비기능 요구사항, 기능별 완료조건, 범위 제외 목록을 반영했다. 고객 가치·우선순위·역할은 검증 또는 합의 전 제안임을 구분했다. 개인별 기여는 확인되지 않아 만들지 않았다. 3분 공유 시 2·7·12장을 중심으로 설명하고 상세 표는 질의응답에 활용할 수 있다.

구현 범위는 README, `docs/security_limitations.md`, `docs/validator_agent.md`, `docs/pqc_audit_integrity.md`, 관련 API·테스트를 기준으로 설명한다. Validator는 LLM/Mock 생성 후 반환 전의 규칙 기반 출력 검증 계층이다. SSE는 전체 버퍼링 후 검증한다. 감사 로그는 원문 prompt·response·API key·system prompt·개인정보를 저장하지 않는 원칙을 유지한다.

현재 서명은 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**다. 실제 ML-DSA, PQC TLS 및 운영 보안 보장을 주장하지 않는다.

## 평가 수치의 취급

- 내부: `reports/evaluation_report.md`의 2026-07-28 내부 113건 기록을 인용. reason-code 집계이며 운영 일반화 성능이 아님.
- 외부: `reports/external_prompt_injection_report.md`의 deepset 전체 662건 기존 결과를 별도 슬라이드에 인용. PII·내부 회귀·external-tuned 성능과 혼합하지 않음.
- ProtectAI F1은 README 0.3227과 외부 보고서 0.2950이 불일치한다. 수정 전에 사용자에게 경고했고 해당 값은 PPT 수치 표에서 제외했다. 원본 README·보고서는 변경하지 않았다.
- 탐지 로직·데이터·평가 스크립트는 변경하지 않았다. 기존 성능 수치의 출처를 명시했고 성능 평가를 새로 수행하지 않았다. 현행 로컬 classifier가 수정 상태이므로 과거 결과를 현행 모델 재평가 결과로 해석할 수 없다.
- 시연 화면은 `docs/images/demo_proxy_mask_phone.png`의 과거 저장 결과이며 Mock 응답임을 표시했다.

## 검증

2026-10-12 다음 명령을 실행했다.

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_proxy_analyze_api.py backend/tests/test_validator_agent.py backend/tests/test_audit_integrity.py backend/tests/test_sse_proxy_api.py -q
git diff --check
git status --short --branch
```

관련 pytest: **17 passed, 7 warnings**. FastAPI startup 이벤트와 NumPy 배열 shape 사용 중단 예정 경고가 남는다. 전체 테스트·실제 OpenAI 호출·운영 부하 테스트는 수행하지 않았다.

PPTX 패키지·기하·글꼴·편집 가능한 표·재가져오기 검사가 최종 통과했고 12장 PNG 렌더링을 모두 육안 확인했다. 초기 파일 검사에서 표 검증 옵션 누락과 글꼴 내보내기 불일치를 발견해 수정했다. 재가져오기 검사에 필요한 런타임 경로 환경변수 누락도 보완 후 통과했다. 시스템 `python` 명령을 찾지 못해 번들 Python으로 강의자료를 정상 추출했다. PowerPoint 앱에서 직접 열어 확인하지는 않았다.

기존 `models/lightweight/classifier.joblib` 변경과 `.worktrees/`는 이번 커밋에서 제외한다.
