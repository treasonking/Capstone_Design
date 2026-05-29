# Validator Agent and PQC Extension Scope

본 연구의 핵심 평가는 공공기관·사내망 환경에서 개인정보가 외부 LLM 또는 내부 LLM으로 원문 그대로 전달되지 않도록 프록시가 입력 탐지, 마스킹, 차단, 출력 검사, 정책 결정, 감사로그 기록을 수행하는 구조에 집중한다.

Validator Agent와 PQC 기반 감사로그 무결성 구조는 탐지 성능을 높이는 핵심 기법이 아니라, 실제 운영 환경에서 프록시 정책 결정의 신뢰성, 감사 가능성, 로그 무결성을 높이기 위한 확장 요소이다.

## Scope

| 항목 | 본 연구에서의 위치 | 정량 성능 비교 포함 여부 | 후속 연구 |
|---|---|---|---|
| Validator Agent | `action`과 `reason_code`가 정책 기준에 부합하는지 재검증하는 운영형 확장 요소 | 제외 | 적용 전후 오탐·미탐 변화, 출력 검증 latency, SSE 버퍼링 비용 평가 |
| PQC-compatible audit signature | 원문을 저장하지 않는 감사로그의 사후 위·변조 가능성을 줄이기 위한 무결성 확장 요소 | 제외 | 실제 ML-DSA 적용, 서명·검증 latency, 키 관리, 서명 크기 평가 |

## Existing Proxy와 Validator Agent의 역할 분리

| 항목 | Existing Proxy | Validator Agent |
|---|---|---|
| 연구 질문 | 입력 단계에서 위험을 얼마나 잘 탐지하고 정책 처리하는가 | 출력 단계에서 정책 결정과 응답 안전성을 얼마나 일관되게 재검증하는가 |
| 데이터셋 | PII 시나리오 데이터셋, Prompt Injection 공개 데이터셋 | 출력 검증 전용 데이터셋이 필요 |
| 지표 | Precision, Recall, F1, Accuracy, latency | output FP/FN, policy consistency, output validation latency |
| 현재 논문 포함 | 포함 | 정량 비교 제외 |
| 향후 연구 | 탐지 범위 확장 | Validator 전용 벤치마킹 설계 |

Validator Agent를 정량 평가하려면 기존 입력 탐지 데이터셋과 별도로 출력 응답 데이터셋이 필요하다. 예를 들어 LLM 응답 안에 마스킹 누락, 개인정보 재노출, 시스템 프롬프트 노출, 정책 위반 답변이 포함된 사례를 구성해야 한다. 따라서 본 연구에서는 Validator Agent를 정량 성능 비교에 포함하지 않고, 후속 연구로 분리한다.

## Interpretation

Validator Agent는 LLM 응답 생성 후 최종 반환 전에 실행되지만, 탐지 모델 자체를 대체하거나 독립적인 성능 향상을 보장하는 요소는 아니다. 따라서 본 보고서에서는 Validator Agent를 PII 탐지 또는 Prompt Injection 탐지 정량 비교 대상에 포함하지 않는다.

PQC 기반 감사로그 서명 구조는 개인정보 탐지 성능을 높이는 요소가 아니다. 현재 구현은 ML-DSA 교체 가능한 감사 로그 서명 인터페이스와, 내부적으로 HMAC-SHA256을 사용하는 `MOCK-ML-DSA` signer 기반 검증 구조다.

## Paper-Ready Wording

본 연구에서는 개인정보 유출 방지 프록시의 입력 탐지, 출력 검사, 정책 결정, 감사로그 구조를 중심으로 평가하였다. Validator Agent와 PQC 기반 감사로그 무결성 구조는 실제 운영 환경에서의 신뢰성과 추적성을 높이기 위한 확장 요소로 설계하였다.

Validator Agent는 프록시의 `action`과 `reason_code`가 정책 기준에 부합하는지 재검증하기 위한 구조이며, 탐지 모델 자체를 대체하거나 독립적인 성능 향상을 보장하는 요소는 아니다. 따라서 본 연구에서는 Validator Agent를 정량 성능 비교 대상에서 제외하고, 적용 전후 오탐·미탐 변화와 latency를 평가하는 별도 벤치마킹을 향후 연구로 둔다.

기존 Proxy는 사용자 입력이 LLM으로 전달되기 전에 개인정보와 Prompt Injection 위험을 탐지하고, 정책 엔진을 통해 입력 기준 조치인 `input_action`을 결정한다. 반면 Validator Agent는 LLM 응답 생성 이후 최종 사용자 반환 전에 동작하는 후단 검증 계층으로, 출력 내 개인정보 잔존 여부, 정책 위반 응답, 마스킹 누락 여부를 재검사하여 `output_action`을 산출한다. 최종 조치인 `final_action`은 `input_action`과 `output_action`을 종합하여 결정된다. 따라서 Validator Agent는 기존 Proxy를 대체하는 탐지 모델이 아니라, 운영 환경에서 정책 결정의 일관성과 감사 가능성을 높이기 위한 확장 요소로 해석한다.

본 연구의 정량 평가는 입력 탐지와 정책 처리 결과를 중심으로 수행하였으며, Validator Agent 자체의 적용 전후 오탐·미탐 변화, 출력 검증 latency, policy consistency 개선 정도는 별도 출력 검증 데이터셋이 필요한 후속 연구로 둔다.

PQC 기반 감사로그 서명 구조는 개인정보 탐지 성능을 높이는 요소가 아니라, 원문을 저장하지 않는 감사로그의 사후 위·변조 가능성을 줄이기 위한 무결성 확장 요소이다. 현재 구현은 ML-DSA 교체 가능한 인터페이스와 Mock signer 기반 검증 구조를 포함하며, 실제 PQC 알고리즘 적용 및 성능 평가는 후속 연구로 남긴다.
