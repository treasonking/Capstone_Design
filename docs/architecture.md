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
6. action이 `MASK`이면 민감정보를 치환한 뒤 upstream LLM으로 전달한다.
7. action이 `BLOCK`이면 upstream LLM 호출 없이 차단 응답을 반환한다.
8. action이 `ALLOW`이면 요청을 그대로 upstream LLM으로 전달한다.
9. LLM 또는 Mock LLM 응답 생성 이후 Validator Agent가 최종 사용자 반환 전에 정책 결정 결과와 출력을 재검사한다.
10. Validator Agent는 핵심 탐지 모델이 아니라, 출력 내 PII 잔존, 시스템 프롬프트 또는 내부 정책 노출, 정책 우회 성공 징후, 마스킹 누락을 확인하는 운영형 확장 요소이다.
11. 최종 응답 이후 audit log에는 `input_action`, `output_action`, `final_action`, Validator Agent 결과가 분리 기록되고, Mock signer 기반 integrity signature가 추가된다.

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

PQC 기반 감사로그 서명 구조는 탐지 성능 개선이 아니라 감사 로그 무결성 검증을 위한 확장 기능이다. 현재 개발 구현은 `HMAC-SHA256-MOCK` signer이며 `MOCK_ONLY`로 명시한다. 실제 ML-DSA 라이브러리를 탑재한 것이 아니라, ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조이다. 실제 PQC 알고리즘 적용 및 성능 평가는 후속 연구 범위다.

Docker Compose의 호스트 바인딩은 Proxy `127.0.0.1:8000`, Mock LLM `127.0.0.1:8001`이다. 컨테이너 사이 통신은 Compose 서비스 이름을 사용한다.
