# Codex 작업 기록 — 주민센터 공식자료 보강

## 작업 목표

기존 주민센터 안내 10개 업무를 공식 공개자료로 보강하고, 전국 공통 제도와 지역 사례의 적용 범위를 구분한다.
특정 센터의 운영정보를 지어내지 않고 기존 보안 프록시 안에서 자료를 사용한다.

## 현재 상태와 범위

- Confirmed: 공개자료 10건, 서버 키워드 검색, 입력 검사·egress 마스킹·출력 Validator·최소 감사 로그 경로가 존재했다.
- 이번 변경: 7개 전국 공통 안내와 3개 지역 참고자료, 대조 방식과 추가 근거, 출처 범위 표시, 기관 운영정보 미등록 지침.
- Not verified: 실제 OpenAI 답변 품질, 근거 준수, 법령 전체의 현행성, 특정 행복 주민센터 운영정보.
- 보존: API 계약·인증·정책 결정·탐지기·Provider 선택·이력 제한·SSE 버퍼링·감사 로그·Mock signer 구조.

## 구현 파일

| 파일 | 목적 |
|---|---|
| `backend/app/data/resident_center_services.json` | 10개 업무 내용·지역·범위·접근 방식·추가 출처 |
| `backend/app/services/resident_center_agent.py` | 범위별 지침, 미등록 센터정보 지침, 적용 범위·추가 URL 표시 |
| `backend/tests/test_resident_center_agent.py` | 변경된 공식 출처, 인증 API의 범위 표시와 보조 근거, 자료 추적성 회귀 |
| `docs/resident_center_sources.md` | 공식 URL, 접근 한계, 지역 혼용 위험, 갱신 절차 |
| `README.md`, `docs/resident_center_agent.md`, `docs/security_limitations.md` | 실행 방식·검증 한계와 설명 동기화 |
| `reports/resident_center_sources_verification.md` | 실제 명령과 결과, 재현 범위 |

## 필수 검증과 완료 기준

- 기존 25개 합성 민원·후속·PII·공격 사례와 기존 관련 회귀를 유지한다. 합격을 위해 기대 action이나 라벨을 바꾸지 않는다.
- Provider를 합성 응답으로 대체한 통합 검증은 실제 모델 정확성 검사로 보고하지 않는다.
- 화면 회귀, JSON 파싱, `git diff --check`를 실행한다.
- 자료 개수·ID와 출처 추적성, 전국/지역 범위가 최종 검사된 응답에 표시되는지 검증한다.
- 원문 민원·응답·검색어를 감사 로그에 추가하지 않는다.
- 기존 탐지 benchmark는 그대로 두며 이번 결과와 합산하지 않는다.

## 후속 Codex 작업

실제 센터의 시·군·구·동과 공식 페이지가 정해진 뒤 센터 운영정보를 등록한다. 운영정보 입력에는 출처·확인일·
적용 지역을 필수로 하고 미확인 값은 비워 둔다. 승인된 모델 환경에서 일반 민원·대리·온라인 제한·
미수록 업무·타지역·운영시간 질문을 실제로 실행해 답변과 자료의 일치 여부를 별도로 평가한다.
실제 개인정보나 API 키를 증거 파일·프롬프트 샘플에 넣지 않는다.

## 완료 상태

자료·코드·문서 보강 및 관련 회귀 검증 완료. 정확한 실행 수치와 미검증 항목은
[검증 보고서](../reports/resident_center_sources_verification.md)를 기준으로 한다.

## 후속 확대 완료 기록

2026-11-03 추가 요청으로 자료를 30개 업무로 확대했다. 이 문서의 10건·검증 수치는 당시 기록이며, 현재 범위와 실행 결과는 [확대 Codex 기록](codex_resident_center_expansion.md)과 [확대 검증 보고서](../reports/resident_center_expansion_verification.md)를 따른다.
