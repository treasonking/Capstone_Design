# Codex Workflow

이 문서는 Capstone_Design 저장소에서 Codex가 보안 프로젝트 운영자처럼 일하기 위한 절차다. 이 프로젝트의 핵심은 공공기관·사내망 환경에서 LLM 사용 중 개인정보 유출과 프롬프트 인젝션 위험을 줄이는 서버형 보안 프록시다.

## 1. 작업 시작

먼저 현재 브랜치, 변경 상태, 관련 파일 구조를 확인한다.

```powershell
git status --short --branch
rg --files -uu
```

기존 변경이 있으면 사용자 작업으로 간주하고 되돌리지 않는다. 작업 대상과 관련된 README, docs, reports, evaluation 파일을 읽은 뒤 수정한다.

## 2. 기능 범위 구분

작업 중에는 다음 범주를 항상 분리한다.

| 범주 | 설명 | 주의 |
|---|---|---|
| PII 탐지 | 주민등록번호, 전화번호, 이메일, 주소, 계좌번호, 민원정보 등 개인정보 탐지와 마스킹 | Prompt Injection 성능과 섞지 않는다 |
| 프롬프트 인젝션 탐지 | 지시 무시, 시스템 프롬프트 탈취, 정책 우회, jailbreak 탐지 | 보안 설명 문장 hard negative를 함께 고려한다 |
| Validator Agent | LLM 또는 Mock LLM 응답 생성 이후 최종 반환 전 출력 검증 | 실시간 스트리밍 검증인지 버퍼링 후 검증인지 명시한다 |
| Mock 무결성 | `HMAC-SHA256-MOCK` signer와 ML-DSA 교체 가능 인터페이스 | 실제 PQC 또는 ML-DSA 구현으로 쓰지 않는다 |
| 감사 로그 | 정책 판정과 integrity metadata를 남기는 추적 계층 | raw prompt, raw response, API key, system prompt, 개인정보 원문 저장을 주장하지 않는다 |

## 3. 문서와 수치 관리

성능 수치는 반드시 실제 산출물에서 가져온다.

허용 출처:

- `reports/*.csv`
- `reports/*.json`
- `reports/*.md`
- evaluation 명령 출력
- pytest 또는 검증 스크립트 출력

README와 reports의 수치가 다르면 즉시 수정하지 말고 차이를 먼저 알린다. 수치를 맞출 때는 어떤 파일이 source of truth인지 명시하고, 관련 README, docs, reports를 함께 갱신한다.

내부 회귀 데이터셋, 24건 외부 스타일 예비 검증셋, Hugging Face 공개 데이터셋, external-tuned 모델 결과는 목적이 다르다. 외부 공개 데이터셋 성능을 한국어 공공기관 운영 일반화 성능처럼 쓰지 않는다.

## 4. README 보호 규칙

다음 항목은 임의로 삭제하지 않는다.

- Docker 실행 명령어
- 평가 실행 명령어
- README 주요 섹션
- 성능 결과 해석 주의
- 운영 가드레일 및 보안 한계
- Validator Agent와 PQC 관련 한계 문장

큰 구조 변경이 필요하면 기존 내용을 다른 문서로 이동하고 README에는 이동 위치를 남긴다.

## 5. 구현 규칙

코드 변경은 기존 구조를 우선 따른다.

- detector 변경은 `backend/app/detection/`와 관련 테스트를 함께 확인한다.
- Validator Agent 변경은 `backend/app/validator/`, proxy 흐름, audit summary를 함께 확인한다.
- PQC 또는 audit integrity 변경은 `backend/app/integrity/`, `backend/app/services/audit_service.py`, `tools/verify_audit_log.py`를 함께 확인한다.
- 평가 변경은 `evaluation/`, `reports/`, `docs/evaluation_method.md`, `docs/evaluation_limitations.md`를 함께 확인한다.

Mock 또는 fallback 경로를 바꾸면 사용자-facing 문서에도 Mock/fallback 상태를 명확히 남긴다.

## 6. 검증 규칙

코드 수정 후에는 관련 focused pytest를 실행한다. 예시는 다음과 같다.

```powershell
python -m pytest backend/tests/test_pii_detector.py backend/tests/test_injection_detector.py
python -m pytest backend/tests/test_validator_agent.py
python -m pytest backend/tests/test_pqc_signer.py backend/tests/test_audit_integrity.py
```

탐지 성능, 데이터셋, 평가 스크립트, README 성능표를 수정했다면 관련 평가 명령을 실행한다.

```powershell
python -m evaluation.evaluate --dataset evaluation/sample_dataset.json --report reports/evaluation_report.md
python -m evaluation.evaluate --dataset evaluation/external_validation_sample.json --report reports/external_validation_report.md
python -m evaluation.baseline_compare --report reports/baseline_compare_report.md --results reports/baseline_compare_results.json
```

문서 또는 설정만 바꾼 경우에도 최소 검증을 실행한다.

```powershell
git diff --check
git status --short --branch
```

검증 실패가 있으면 완료로 포장하지 않고 실패 명령과 남은 리스크를 기록한다.

## 7. GitHub 업데이트

작업이 끝나면 변경 내용을 검토한 뒤 커밋하고 현재 브랜치에 푸시한다.

```powershell
git diff --stat
git add <changed-files>
git commit -m "<type>: <summary>"
git push
```

네트워크, 권한, 충돌, 승인 문제로 푸시하지 못하면 로컬 변경 상태와 필요한 후속 명령을 최종 응답에 남긴다.

## 8. 최종 응답

최종 응답에는 반드시 다음 표를 포함한다.

| 변경 요약 | 수정 파일 | 검증 결과 | 남은 리스크 |
|---|---|---|---|
| 무엇을 바꿨는지 요약 | 변경 파일 목록 | 실행한 검증 명령과 통과/실패 | 남은 제한, 확인 필요, 미실행 항목 |
