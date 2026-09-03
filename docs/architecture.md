# 다층형 탐지 파이프라인 아키텍처

본 시스템은 다층형 탐지 파이프라인(Multi-layered Detection Pipeline)을 기반으로 한다. 여러 탐지기를 단순히 병렬 실행하는 구조가 아니라, 정규식 패턴 계층, 휴리스틱 규칙 계층, 경량 분류 계층, 의사결정 계층을 순차적으로 통과하며 각 계층의 결과를 다음 판단에 반영한다.

## 계층 구성

| 계층 | 명칭 | 목적 | 주요 탐지 대상 |
|---|---|---|---|
| 1 | 정규식 패턴 계층 | 형식이 명확한 개인정보를 빠르게 탐지 | 주민등록번호, 전화번호, 이메일, 계좌번호 |
| 2 | 휴리스틱 규칙 계층 | 키워드 조합과 문맥 단서를 기반으로 위험 판단 | 정책 우회, 시스템 프롬프트 탈취, 지시 무시 |
| 3 | 경량 분류 계층 | 패턴 기반으로 탐지하기 어려운 문장형 공격 분류 | 우회형 인젝션, 문맥형 공격, 애매한 악성 지시 |
| 4 | 의사결정 계층 | 각 계층의 탐지 결과를 종합하여 정책 적용 | ALLOW, MASK, BLOCK, WARN |

## 탐지 순서

1. 입력 요청을 수신한다.
2. Regex Pattern Layer에서 정형 PII를 우선 탐지한다.
3. Heuristic Rule Layer에서 프롬프트 인젝션 키워드, 정책 우회 문장, 조합 규칙을 탐지한다.
4. Lightweight Classification Layer에서 비정형 또는 애매한 문장을 분류한다.
5. Decision Layer에서 탐지 결과를 종합하고 `BLOCK > MASK > WARN > ALLOW` 순서로 최종 action을 결정한다. 정책 파일의 숫자 priority는 같은 action 안에서만 우선순위를 정한다.
6. action이 `MASK`이면 민감정보를 치환한 안전 입력만 Provider 계층으로 전달한다.
7. action이 `BLOCK`이면 upstream LLM 호출 없이 차단 응답을 반환한다.
8. action이 `ALLOW`이면 요청을 Provider 계층으로 전달한다.
9. 고정 allowlist Registry가 서버 환경변수 `LLM_PROVIDER`에 따라 `mock` 또는 `openai` 어댑터를 선택한다.
10. Provider가 전체 응답을 반환한 뒤 Validator Agent가 최종 사용자 반환 전에 정책 결정 결과와 출력을 재검사한다.
11. Validator Agent는 핵심 탐지 모델이 아니라, 출력 내 PII 잔존, 시스템 프롬프트 또는 내부 정책 노출, 정책 우회 성공 징후, 마스킹 누락을 확인하는 운영형 확장 요소이다.
12. 최종 응답 이후 audit log에는 정책과 Provider 메타데이터가 분리 기록되고, Mock signer 기반 integrity signature가 추가된다.

## Provider 계층

`backend/app/providers/`는 정책·API 라우터와 특정 SDK의 결합을 끊는다.

| 파일 | 역할 |
|---|---|
| `base.py` | `LLMProvider`, `ProviderRequest`, `ProviderResponse` 공통 계약 |
| `mock_provider.py` | 기존 로컬 Mock LLM HTTP 호출과 공통 응답 변환 |
| `openai_provider.py` | 공식 OpenAI SDK의 Responses API 어댑터 |
| `registry.py` | `mock`, `openai`만 허용하는 고정 Registry |
| `errors.py` | 인증, Rate Limit, timeout, upstream, invalid response 오류 표준화 |

Provider는 요청 본문이 아니라 서버 환경변수 `LLM_PROVIDER`로 선택한다. 요청의 `model` 값은 기존 API 스키마 호환을 위해 수신하지만 Provider 선택이나 OpenAI 모델 변경에 사용하지 않는다. OpenAI 모델은 `OPENAI_MODEL`에서만 읽고, 사용자가 URL이나 외부 endpoint를 지정하는 경로는 없다. 자동 Provider 라우팅과 다른 사업자로의 자동 폴백은 구현하지 않았다.

Provider 직전 egress guard는 정책의 `MASK` 결과뿐 아니라 위치가 확인된 모든 PII 탐지 span을 다시 마스킹한다. `PII_ACCOUNT_DETECTED=WARN`처럼 정책이 경고인 경우에도 외부 Provider에는 마스킹된 값만 전달한다. 모델 단독 PII 신호처럼 치환 위치를 확정할 수 없으면 `PII_UNMASKABLE_DETECTED`로 fail-closed 차단하고 Provider를 호출하지 않는다.

OpenAI 어댑터는 `AsyncOpenAI.responses.create`에 정책 처리된 입력, 시스템 지시, `store=False`, `max_output_tokens`, 요청별 timeout을 전달한다. SDK 자동 재시도는 0회로 제한한다. 응답 텍스트, Provider, 실제 응답 모델, 지연 시간, 종료 상태, 토큰 사용량, 비민감 응답 ID를 공통 응답으로 변환하지만 원문과 응답 ID는 감사 로그에 저장하지 않는다.

## Existing Proxy와 Validator Agent의 경계

Validator Agent는 입력 탐지 파이프라인의 일부가 아니라 LLM 응답 이후의 출력 검증 계층이다. 따라서 외부 데이터셋 기반 Prompt Injection 탐지 성능 평가는 입력 탐지 파이프라인을 중심으로 수행하며, Validator Agent 자체의 성능 벤치마킹은 별도 후속 연구로 분리한다.

| 구분 | Existing Proxy | Validator Agent |
|---|---|---|
| 위치 | 사용자 입력이 LLM으로 전달되기 전 | LLM 응답 생성 후 사용자에게 반환되기 전 |
| 주요 역할 | 입력 탐지, 마스킹, 차단, 정책 결정 | 출력 검증, 정책 결정 재검토 |
| 검사 대상 | 사용자 입력 prompt | LLM 응답 output |
| 대표 필드 | `input_action`, `reason_code` | `output_action`, `validator` |
| 최종 조합 | 입력 기준 정책 결정 | `input_action`과 `output_action`을 종합해 `final_action` 결정 |
| 연구 내 위치 | 핵심 평가 대상 | 운영형 확장 요소 |

## 구현 메모

현재 코드에는 기존 구현 호환성을 위해 `backend/app/detection/hybrid_detector.py`와 `hybrid_detection` audit 필드명이 남아 있다. 문서상 대표 명칭은 다층형 탐지 파이프라인이며, 본 시스템은 정책·패턴 기반 탐지와 경량 분류를 결합한다는 점에서 넓은 의미의 하이브리드 구조로만 설명한다.

Validator Agent는 입력 검사 전에 배치하지 않는다. 입력 검사는 detector와 policy engine이 담당하고, Validator Agent는 LLM 출력 생성 이후에만 실행되는 정책 결정 재검증 계층이다. 본 연구의 핵심 정량 평가 대상은 아니며, Validator Agent 자체 벤치마킹은 후속 연구로 둔다.

`/proxy/analyze`는 LLM 호출이 없는 사전 분석 API이므로 Validator Agent 출력 재검사는 `SKIPPED`로 기록된다.

SSE 엔드포인트는 보안 검증을 위해 upstream 응답 전체를 버퍼링한 뒤 Validator Agent 검증 후 안전한 응답만 반환한다. 차단된 입력은 upstream을 호출하지 않으며, 출력이 차단되면 원본 token event를 보내지 않는다. 따라서 실시간 토큰 스트리밍이 아니라 검증 후 일괄 반환 구조에 가깝다.

감사 로그에는 `provider`, `model`, `upstream_called`, `upstream_status`, `upstream_latency_ms`, `input_decision`, `output_decision`, `reason_codes`, `error_type` 등 메타데이터만 기록한다. API key, Authorization header, 원본·마스킹 전 입력, 원본 Provider 응답, system instructions, SDK 오류 객체는 기록하지 않는다.

PQC 기반 감사로그 서명 구조는 탐지 성능 개선이 아니라 감사 로그 무결성 검증을 위한 확장 기능이다. 현재 개발 구현은 `HMAC-SHA256-MOCK` signer이며 `MOCK_ONLY`로 명시한다. 실제 ML-DSA 라이브러리를 탑재한 것이 아니라, ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조이다. 실제 PQC 알고리즘 적용 및 성능 평가는 후속 연구 범위다.

Docker Compose의 호스트 바인딩은 Proxy `127.0.0.1:8000`, Mock LLM `127.0.0.1:8001`이다. 컨테이너 사이 통신은 Compose 서비스 이름을 사용한다.
