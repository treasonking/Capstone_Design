# Current Verification Report

- 점검일: 2026-09-03 (Asia/Seoul)
- 브랜치: `codex-validator-pqc-audit-integrity`
- 변경 시작 기준 커밋: `fd09902` (`master`보다 36커밋 앞섬, 뒤처짐 0)
- 실행 환경: Windows, Python 3.12.13, scikit-learn 1.7.2, openai 2.54.0
- 기준 문서: 로컬에서 발견된 `LLM_보안_프록시_기술문서_서영동.docx`
- 기준 문서 SHA-256: `A6134A75C54F2D658B0F856AAF3D65ADF639CB7A4C05F92DC3849069C7050A83`

요청된 파일명 `LLM_보안_프록시_기술문서_서영동(1).docx`는 작업 디렉터리와 다운로드 폴더에서 찾지 못했다. 동일 제목의 `(1)` 없는 문서를 읽기 전용 기준으로 사용했다. 저장소 밖 DOCX는 수정하지 않았으며, 코드 기준 정정 사항은 이 보고서와 저장소 Markdown 문서에 반영했다.

## 1. 초기 상태

실제 Proxy 진입점은 `backend.app.api.proxy:app`, Mock LLM 진입점은 `tools.mock_llm:app`이다. 주요 API는 `POST /proxy/analyze`, `POST /proxy/chat`, `POST /proxy/chat/stream`, `POST /v1/chat/completions`와 관리자 조회 API다. PII 탐지는 `backend/app/detection/pii_detector.py`, Injection 탐지는 `backend/app/detection/injection_detector.py`, 결합은 `hybrid_detector.py`와 `lightweight_classifier.py`, 정책은 `backend/app/engine/policy_engine.py`, 출력 검증은 `backend/app/validator/`와 `proxy_service.py`에 있다. Provider 공통 계약과 Registry는 `backend/app/providers/`에 있으며 실제 구현 Provider는 Mock과 OpenAI뿐이다.

기본 경량 분류기는 `models/lightweight/vectorizer.joblib`, `models/lightweight/classifier.joblib`을 joblib으로 로드한다. artifact 누락·비활성·의존성 오류 시 실행을 중단하지 않고 rule/fallback 경로로 내려가며, 이 상태는 완전한 Hybrid 성능으로 해석하면 안 된다.

작업 시작 시 `models/lightweight/classifier.joblib`은 이미 수정된 작업 트리 상태였다. 이 파일은 이번 점검에서 재학습하거나 덮어쓰지 않았고, 현행 평가가 실제 로컬 artifact를 사용했다는 사실을 결과 해석에 남긴다.

| 현행 로컬 artifact | SHA-256 |
|---|---|
| `models/lightweight/classifier.joblib` | `02F814970B8596C07DB774EE185EC25DD777734E462F8EFE9CB399321A1AA67E` |
| `models/lightweight/vectorizer.joblib` | `0C1DC0923651E90EB7023842BD936D21177CB55681460915141C7EA37079CE14` |
| `models/lightweight_external_tuned/classifier.joblib` | `D777989A1F67D172FFC22EE29EA6BB88F0A7FD15C13095E563C2BA8568B71EAD` |
| `models/lightweight_external_tuned/vectorizer.joblib` | `DB517A73CF4216738BF0840BE94256950CEF6816F7CED41DC02E75C96025867F` |

## 2. 수정 전 갭 분석

| 요구사항 | 현재 구현 | 상태 | 문제점 | 수정 대상 |
|---|---|---|---|---|
| 입력→정책→LLM→출력 Validator→최종 정책→감사 | `process_proxy_chat`과 stream 경로에 순서 구현 | 완료 | 문서에서 SSE를 실시간처럼 오해할 여지 | `docs/architecture.md`, `docs/validator_agent.md` |
| 입력 BLOCK 시 upstream 미호출 | BLOCK 분기에서 호출 생략 | 완료 | 직접 호출 방지 회귀 테스트 보강 필요 | `backend/tests/test_proxy_api.py` |
| PII 및 필수 reason code | RRN, 전화, 이메일, 난독화 이메일과 추가 계좌·주소 등 구현 | 완료 | 감사 로그에 유형별 건수 부족 | `proxy_service.py`, `audit_service.py` |
| Injection 규칙+경량 모델 | 한국어·영어·혼합 규칙과 sklearn artifact 결합 | 완료 | artifact 버전 결합 및 외부 일반화 한계 | 문서·평가 보고서 |
| `BLOCK > MASK > WARN > ALLOW` | 정책 규칙 priority와 action weight 사용 | 부분 | 높은 YAML priority의 약한 action이 강한 action을 이길 수 있음 | `policy_engine.py` |
| 출력 Validator와 SSE 보호 | 전체 출력 버퍼링 후 검증 | 완료 | 입력·출력 BLOCK 시 token event 비노출 테스트 보강 | `test_sse_proxy_api.py` |
| 감사 로그 최소 필드·원문 미저장 | action/reason/latency/서명과 요약 저장 | 부분 | PII·Injection 건수, block/error 유형 부족; raw `user_id` 저장 가능 | `audit_service.py`, `proxy_service.py` |
| HMAC-SHA256 무결성 | HMAC 기반 Mock signer와 verify 도구 구현 | 부분 | `MOCK-ML-DSA` 알고리즘명과 클래스명이 실제 구현을 오해시킴; 개발 키 한계 불명확 | `pqc_signer.py`, `audit_signer.py`, 문서 |
| Docker Compose 8000/8001 | 서비스 분리 및 포트 일치 | 부분 | 호스트 전체 인터페이스에 포트 공개 | `docker-compose.yml` |
| 단위·통합·보안 회귀 | 폭넓은 pytest 존재 | 부분 | action 우선순위, upstream 비호출, audit 가명화·원문 재귀 제거 검증 부족 | `backend/tests/` |
| README·기술문서와 코드 일치 | 주요 구조는 대체로 일치 | 부분 | 과거 테스트 수치, PQC 표기, 평가 생성 시점과 현재 산출물 불일치 | README, docs, reports |

## 3. 구현 보완

| 파일/영역 | 변경 | 보안 목적 |
|---|---|---|
| 정책 엔진 | winner key를 action 강도 우선으로 변경 | 숫자 priority와 무관하게 `BLOCK > MASK > WARN > ALLOW` 보장 |
| Proxy audit summary | PII·Injection 탐지 건수, `block_type`, `error_type` 추가 | 차단과 upstream 오류 구분 및 유형별 추적 |
| 감사 로그 | `user_id` HMAC 가명화, 중첩 hybrid summary까지 금지 필드 재귀 제거 | 원문 신원·PII·API key 저장 위험 축소 |
| Mock signer | `MockAuditSigner`, `HMAC-SHA256-MOCK`, `MOCK_ONLY`, `replacement_target=ML-DSA` | 실제 PQC 구현이라는 오해 방지 |
| Docker Compose | 호스트 바인딩을 127.0.0.1로 제한 | 개발 서비스의 외부 노출 축소 |
| 의존성 | 기본 artifact 생성 버전에 맞춰 scikit-learn 1.7.2 고정 | 기본 runtime 재현성 향상 |
| 테스트 | action 우선순위, no-upstream BLOCK, SSE no-token BLOCK, audit 원문 미저장, HMAC 검증 강화 | 핵심 보안 불변식 회귀 방지 |
| Provider 추상화 | 공통 request/response, 고정 Registry, 표준 오류 코드 | 정책·라우터와 특정 SDK 분리, 요청값 기반 URL 선택 차단 |
| OpenAI 어댑터 | 공식 SDK Responses API, `store=False`, timeout, 출력 토큰 상한, 재시도 0회 | 안전 입력만 전송하고 완성 응답을 Validator 전단에 연결 |
| Provider egress guard | WARN 포함 모든 위치 기반 PII 재마스킹, 위치 불명 PII fail-closed | 마스킹 전 개인정보의 외부 전송 방지 |
| Provider 감사 메타데이터 | provider/model/call/status/latency/결정/error 기록 | 정책 BLOCK과 외부 Provider 장애 분리 |

### Provider 지원 상태

| Provider | 구현 | 자동 테스트 | 실제 API 테스트 | 비고 |
|---|---|---|---|---|
| Mock | 구현 | 통과 | N/A | 기존 로컬 Mock LLM 유지 |
| OpenAI | Responses API 어댑터 구현 | SDK Stub 통과 | Not verified | 실행 조건 세 가지가 모두 충족되지 않아 비용 호출 미실행 |
| Claude | 미구현 | 미실행 | 미실행 | 향후 어댑터 확장 |
| Gemini | 미구현 | 미실행 | 미실행 | 향후 어댑터 확장 |

다중 Provider 자동 라우팅과 자동 폴백은 구현하지 않았다. 서버 환경변수 `LLM_PROVIDER`가 `mock` 또는 `openai`일 때만 Registry가 선택하며, 요청 본문의 `model`은 Provider나 OpenAI 모델을 바꾸지 못한다.

## 4. 기능 재현

`LIGHTWEIGHT_MODEL_ENABLED=false` 조건에서 `POST /proxy/analyze`를 직접 호출해 다음을 확인했다.

| 대표 입력 | 결과 | 주요 reason code | upstream |
|---|---|---|---|
| 일반 업무 문장 | ALLOW | `SAFE_INPUT` | 분석 API이므로 false, `should_call_llm=true` |
| 주민등록번호+정책 우회 | BLOCK | `PII_RRN_DETECTED`, `INJ_POLICY_BYPASS` 및 세부 코드 | false, `should_call_llm=false` |
| 난독화 이메일 | MASK | `PII_EMAIL_OBFUSCATED` | 분석 API이므로 false |

`/proxy/analyze`는 LLM 호출 없는 경로이므로 Validator 출력 검사가 `SKIPPED`인 것은 정상이다.

## 5. 테스트와 실행 검증

| 명령 | 결과 | 해석 |
|---|---|---|
| 변경 전 `python -m pytest -q` | 160 passed, 8 warnings, 33.53s | 작업 전 기준선 통과 |
| 변경 후 `python -m pytest -q` | 174 passed, 1 skipped, 8 warnings, 8.61s | 전체 회귀 통과; live OpenAI 1건 skip |
| Provider/proxy/SSE/audit focused tests | 46 passed, 1 skipped, 7 warnings, 6.45s | Stub 기반 보안·오류·Validator 흐름 통과 |
| 로컬 Mock Provider smoke | `action=ALLOW`, `provider=mock`, `upstream_status=success`, `validator=PASS` | 로컬 Mock 서버를 통한 실제 HTTP 경로 통과, 외부 API 미사용 |
| `python -m compileall -q backend` | 성공 | backend 문법/바이트코드 컴파일 통과 |
| `python -m pip check` | 성공 | 설치 의존성 충돌 없음 |
| `docker compose config` | 성공, Docker config 접근 경고 2건 | 기본 Mock 설정과 127.0.0.1 바인딩 확인 |
| 실제 OpenAI API smoke | Not verified | `RUN_LIVE_OPENAI_TESTS` 비활성, `OPENAI_MODEL` 미설정으로 비용 호출 미실행 |
| `docker compose config` | 성공 | 127.0.0.1:8000/8001 확인; Docker config 접근 경고 1건 |
| `python tools/verify_audit_log.py --log-file logs/audit_log.jsonl` | checked 81, valid 32, invalid 49 | 로컬 파일에 과거·다른 테스트 키·구형 포맷 레코드 혼재; 현행 단위 테스트의 신규 서명·변조 검사는 통과 |

8개 warning은 FastAPI/Starlette 수명주기·TestClient deprecation 3건과 joblib/numpy artifact loading 관련 warning 5건이다. 테스트 실패로 숨기지 않으며, 향후 lifespan API 전환, httpx2 전환, artifact 재학습으로 제거해야 한다.

## 6. 현재 재현 평가

### 내부 및 예비 데이터

| 데이터셋 | 방식/범위 | Precision | Recall | F1 | 재현 여부 |
|---|---|---:|---:|---:|---|
| `evaluation/sample_dataset.json` 113건 | PII reason code | 0.879 | 1.000 | 0.935 | 현재 재현 |
| 동일 | Injection reason code | 0.852 | 1.000 | 0.920 | 현재 재현 |
| `evaluation/external_validation_sample.json` 24건 | PII reason code | 0.875 | 1.000 | 0.933 | 현재 재현, 예비 |
| 동일 | Injection reason code | 0.767 | 1.000 | 0.868 | 현재 재현, 예비 |
| `datasets/sample_dataset_v2.json` 152건 | PII label | 0.979 | 1.000 | 0.989 | 현재 재현 |
| 동일 | Injection label | 0.902 | 1.000 | 0.948 | 현재 재현 |
| 내부 Injection 110건 | Rule Only | 1.000 | 1.000 | 1.000 | 현재 재현, 회귀셋 |
| 동일 | Model Only | 1.000 | 0.127 | 0.225 | 현재 재현 |
| 동일 | Hybrid | 1.000 | 1.000 | 1.000 | 현재 재현 |

확장 회귀셋의 micro 결과는 Precision 0.922, Recall 1.000, F1 0.960이며 false-positive sample 12건, false-negative sample 0건이다.

### 외부 held-out split

현재 재실행은 `datasets/external_splits/eval_external_prompt_injection.jsonl`과 external-tuned artifact를 사용했다.

| 데이터셋 | 방식 | Precision | Recall | F1 | 재현 여부 |
|---|---|---:|---:|---:|---|
| deepset 199건 | Rule Only | 1.0000 | 0.0886 | 0.1628 | 현재 재현 |
| deepset 199건 | Model Only | 1.0000 | 0.1646 | 0.2826 | 현재 재현, 버전 경고 |
| deepset 199건 | Hybrid | 1.0000 | 0.2025 | 0.3368 | 현재 재현, 버전 경고 |
| ProtectAI 969건 | Rule Only | 0.8448 | 0.2344 | 0.3670 | 현재 재현 |
| ProtectAI 969건 | Model Only | 1.0000 | 0.7321 | 0.8453 | 현재 재현, 버전 경고 |
| ProtectAI 969건 | Hybrid | 1.0000 | 0.7392 | 0.8501 | 현재 재현, 버전 경고 |
| Lakera 300건 | Rule Only | N/A | 0.4300 | N/A | 현재 재현, positive-only |
| Lakera 300건 | Model Only | N/A | 0.9467 | N/A | 현재 재현, positive-only·버전 경고 |
| Lakera 300건 | Hybrid | N/A | 0.9500 | N/A | 현재 재현, positive-only·버전 경고 |

external-tuned classifier는 scikit-learn 1.8.0에서 저장되었고 현재 런타임은 1.7.2이므로 `InconsistentVersionWarning`이 발생했다. train/eval ID 중복은 0이지만 정규화 text-hash 중복은 42건(ProtectAI 41, Lakera 1)이다. 이 표는 재실행 증거이지만 운영 일반화나 배포 승인 수치로 사용하면 안 된다.

### 지연 시간

로컬 async stub upstream, 5개 시나리오, 각 5회 warmup 후 30회 측정 결과다.

| 범위 | 평균 | p95 |
|---|---:|---:|
| detector only 전체 | 4.380 ms | 9.923 ms |
| proxy end-to-end 전체 | 84.581 ms | 137.325 ms |

네트워크·실제 LLM 생성 시간은 포함하지 않는다. BLOCK은 upstream을 생략하므로 action별 지연을 같은 조건의 LLM 호출 성능처럼 비교하면 안 된다.

## 7. 기준 DOCX 수치 대조

| 기준 문서 수치 | 저장소 근거 | 2026-07-28 상태 |
|---|---|---|
| 143 passed, 2 warnings | 과거 문서 서술 | 미재현; 현재 174 passed, 1 skipped, 8 warnings |
| Holdout Accuracy 0.833 | 동일 프로토콜 원시 산출물 미발견 | 과거 측정 결과, 현재 미재현 |
| Injection F1 0.923 | 동일 프로토콜 원시 산출물 미발견 | 과거 측정 결과, 현재 미재현 |
| PII F1 0.783 | 동일 프로토콜 원시 산출물 미발견 | 과거 측정 결과, 현재 미재현 |
| SAFE F1 0.783 | 동일 프로토콜 원시 산출물 미발견 | 과거 측정 결과, 현재 미재현 |
| deepset F1 0.14, Recall 7.6% | `reports/external_prompt_injection_report.md`의 F1 0.1413, Recall 0.0760 | 과거 전체셋 결과로 근거 있음; 이번 held-out 프로토콜과 다름 |
| ProtectAI F1 0.32 | README 0.3227, 별도 보고서 0.2950 | 생성 경로가 달라 불일치; 합치지 않음 |

## 8. 감사 로그 보안 경계

현행 신규 레코드는 timestamp, request ID, final decision, reason codes, PII·Injection 건수, latency, block/error type, Provider·model·호출 상태·Provider 지연, 가명 user ID, 무결성 메타데이터를 기록한다. raw prompt, raw response, API key, Authorization header, system prompt, 개인정보 원문, SDK 오류 객체는 저장하지 않으며 중첩 summary도 재귀 검사한다. 저장소 및 `logs/`에서 현재 환경의 API key 문자열을 검색한 결과 일치 항목은 없었다.

현재 HMAC-SHA256은 PQC가 아니다. 정확한 표현은 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**다. 실제 ML-DSA, PQC 키 관리, 서명 성능 평가는 미구현이다.

## 9. 남은 한계

1. external-tuned artifact를 고정 runtime에서 다시 학습하고 모델 해시·학습 데이터·scikit-learn 버전을 함께 배포해야 한다.
2. 외부 split의 exact text overlap을 제거하고 공식 split 또는 별도 독립 테스트셋으로 재평가해야 한다.
3. 레거시 감사 로그의 스키마·키 ID별 마이그레이션과 키 회전 정책이 필요하다.
4. SSE 전체 버퍼링은 원본 토큰 노출을 막지만 first-byte latency와 메모리 사용을 늘린다. 응답 크기 제한과 timeout 정책을 보강해야 한다.
5. 실제 ML-DSA, KMS/HSM 기반 키 관리, 간접 인젝션/RAG 문서 공격, Validator 전용 출력 데이터셋 평가는 아직 구현되지 않았다.
6. 내부 회귀셋의 높은 점수를 운영 일반화 성능으로 주장하면 안 된다.
7. OpenAI 어댑터는 Stub 자동 테스트만 통과했다. 실제 계정의 모델 접근 권한, 비용, 지연, Rate Limit, 데이터 보존 설정은 아직 검증하지 않았다.
8. `store=False`는 Responses application state 저장을 끄지만 조직의 abuse monitoring 및 데이터 제어 조건을 대체하지 않는다.
9. 기본 Docker Compose는 API key를 자동 전달하지 않는다. 컨테이너 운영에는 별도 secret store 또는 Docker secret 통합이 필요하다.
