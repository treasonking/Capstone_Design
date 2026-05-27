# AGENTS.md

항상 끝나면 깃허브 업데이트 하기.

이 저장소는 공공기관·사내망 환경에서의 LLM 기반 개인정보 유출 방지 프록시 서비스를 다루는 보안/캡스톤/포트폴리오 프로젝트다. 모든 에이전트는 기능 구현보다 먼저 프로젝트의 신뢰성과 발표 가능성을 지키는 운영자 관점으로 작업한다.

## 반드시 지킬 원칙

- 구현된 기능, Mock 기능, 미구현 기능을 절대 섞어 설명하지 않는다.
- PII 탐지, 프롬프트 인젝션 탐지, Validator Agent, Mock PQC, 감사 로그를 각각 구분해서 설명한다.
- Mock PQC를 실제 ML-DSA 구현으로 과장하지 않는다. 현재 표현은 "ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조"로 유지한다.
- Validator Agent는 LLM 또는 Mock LLM 응답 생성 이후 최종 반환 전의 출력 검증 계층이다. SSE 경로가 버퍼링 후 검증이면 실시간 토큰 스트리밍 검증처럼 쓰지 않는다.
- 외부 데이터셋 성능과 내부 toy 또는 회귀 데이터셋 성능을 분리한다.
- README와 reports의 수치가 다르면 수정 전 사용자에게 경고하고, 기준 파일을 확인한다.
- 성능 수치는 새로 만들지 않는다. 반드시 실제 CSV, JSON, report, evaluation output, test output에 있는 값만 사용한다.
- 테스트 또는 최소 검증 명령 없이 완료라고 말하지 않는다.
- 논문/발표용 표현에는 한계와 리스크를 함께 작성한다.

## 변경 전 확인

작업을 시작하면 먼저 관련 구조를 확인한다.

```powershell
git status --short --branch
rg --files -uu
```

기능, 성능, 문서, 평가와 관련된 작업은 다음 파일을 우선 확인한다.

- `README.md`
- `docs/evaluation_method.md`
- `docs/evaluation_limitations.md`
- `docs/security_limitations.md`
- `docs/validator_agent.md`
- `docs/pqc_audit_integrity.md`
- `reports/*.md`
- `reports/*.csv`
- `reports/*.json`
- `backend/tests/`

## 문서 관리 규칙

- README, docs, reports, evaluation 결과는 서로 모순되지 않게 관리한다.
- Docker 실행 명령어, 평가 명령어, README 주요 섹션은 임의 삭제하지 않는다.
- 경량 분류 artifact가 없거나 fallback이면 완전한 Hybrid 성능으로 표현하지 않는다.
- `internal`, `external_validation_sample`, Hugging Face 공개 데이터셋, external-tuned 결과를 한 표나 한 문장에 섞을 때는 목적과 한계를 같이 쓴다.
- `/proxy/analyze`는 LLM 호출 없는 사전 분석 API이므로 Validator Agent 출력 재검사 상태가 `SKIPPED`일 수 있음을 보존한다.
- 감사 로그 설명에서는 raw prompt, raw response, API key, system prompt, 개인정보 원문을 저장하지 않는다는 원칙을 유지한다.

## 구현 및 검증 규칙

- 코드 수정 후에는 touched module에 맞는 focused pytest를 실행한다.
- 탐지 로직, 데이터셋, 평가 스크립트, 성능표를 바꾸면 관련 evaluation 명령을 실행하거나 실행하지 못한 이유를 기록한다.
- 문서 또는 설정만 바꾼 경우에도 최소한 `git diff --check`와 `git status --short --branch`를 실행한다.
- 검증 실패를 숨기지 않는다. 실패한 명령, 원인 추정, 남은 리스크를 최종 응답에 남긴다.

## GitHub 업데이트

작업이 끝나면 가능한 경우 변경 사항을 커밋하고 현재 브랜치에 푸시한다. 권한, 네트워크, 충돌, 사용자 승인 문제로 불가능하면 최종 응답에 이유와 필요한 후속 명령을 명시한다.

## 최종 응답 형식

마지막 응답에는 반드시 다음 표를 포함한다.

| 변경 요약 | 수정 파일 | 검증 결과 | 남은 리스크 |
|---|---|---|---|
| 수행한 작업 요약 | 변경한 파일 목록 | 실행한 명령과 결과 | 남은 제한, 실패, 확인 필요 사항 |
