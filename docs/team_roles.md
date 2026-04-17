# Team Roles and Deliverables

## 정책/탐지 리드 (현재 저장소 핵심 반영 영역)

- `policies/policy.yaml` 정책 포맷/우선순위/threshold 설계
- `backend/app/detection/*` PII/Injection 룰 기반 탐지
- `backend/app/engine/*` 정책 판정 및 마스킹
- `evaluation/*` 정량 평가 스크립트/리포트 생성
- `backend/tests/*` 탐지/정책/프록시 테스트

주요 산출물:

- reason_code 체계
- 정책 적용 기준
- 마스킹 규칙
- 탐지 품질 지표(precision/recall/F1)

## 게이트웨이/프록시 리드 (확장 영역)

- FastAPI 라우트/예외 처리
- Upstream 연결 안정성
- 정책 엔진 연동 흐름

## 성능/증빙 리드 (확장 영역)

- latency 수집 및 분석
- 원문 미저장 검증 절차
- 부하 테스트 결과 정리

## QA/통합 리드 (확장 영역)

- 데이터셋 확대/라벨 품질 검증
- E2E 테스트 시나리오 자동화
- 릴리즈 체크리스트 운영

