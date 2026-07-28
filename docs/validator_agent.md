# Validator Agent

Validator Agent is an operational output validation layer that re-checks proxy policy decisions after LLM response generation and before returning the response to the user.

## 정의

Validator Agent는 LLM 또는 Mock LLM이 생성한 출력값을 최종 사용자에게 반환하기 전에 검사하는 정책 기반 보안 검증 계층이다. 핵심 탐지 모델이 아니라, 프록시가 산출한 `action`과 `reason_code`가 정책 기준에 부합하는지 재검증하기 위한 운영형 확장 요소이다.

발표용 문장:

> Validator Agent는 본 연구의 핵심 탐지 모델이 아니라, LLM 응답 생성 이후 최종 사용자 반환 이전 단계에서 프록시 정책 결정의 일관성과 설명 가능성을 재검증하는 운영형 확장 요소이다.

## 연구 범위

Validator Agent는 입력 탐지기, 경량 분류기, 정책 엔진을 대체하지 않는다. 본 연구의 정량 성능 비교는 입력 탐지, 정책 처리 결과, 외부 Prompt Injection benchmark, latency를 중심으로 수행한다.

본 브랜치에서는 Validator Agent 자체의 독립 벤치마킹을 수행하지 않는다. Validator Agent 적용 전후의 오탐·미탐 변화, 출력 검증 latency, SSE 버퍼링 비용은 후속 연구 범위로 둔다.

## Existing Proxy와의 차이

기존 Proxy는 사용자 입력을 LLM으로 전달하기 전에 검사한다. 이 단계에서는 개인정보, Prompt Injection, 정책 우회 표현을 탐지하고, 정책 엔진이 `input_action`과 `reason_code`를 산출한다.

Validator Agent는 LLM 응답이 생성된 이후에 실행된다. 이 단계에서는 출력에 개인정보가 다시 나타나는지, 입력에서 마스킹한 정보가 재노출되는지, LLM이 시스템 프롬프트나 내부 정책을 노출하는지, 정책 우회 성공 응답을 생성했는지를 확인한다.

따라서 Validator Agent는 기존 Proxy의 입력 탐지를 대체하지 않는다. Validator Agent는 출력 검증과 정책 결정 재검증을 담당하는 후단 검증 계층이다.

| 항목 | Existing Proxy | Validator Agent |
|---|---|---|
| 실행 시점 | LLM 호출 전 | LLM 호출 후 |
| 탐지 대상 | 입력 prompt | 출력 response |
| 주요 목적 | 위험 입력 차단 및 마스킹 | 위험 출력 차단 및 정책 재검증 |
| action 필드 | `input_action` | `output_action` |
| audit 기록 | input detector summary | validator summary |
| 연구 평가 | 본 연구의 핵심 정량 평가 대상 | 후속 연구 대상 |

## 배치 위치

```text
사용자 요청
  -> Proxy
  -> 입력 탐지기
  -> 정책엔진
  -> LLM 또는 Mock LLM
  -> Validator Agent
  -> 최종 응답 반환
  -> 감사 로그 저장
```

Validator Agent는 입력 검사 전에 실행하지 않는다. 입력 탐지는 기존 detector와 policy engine이 수행하고, Validator Agent는 LLM 응답 생성 이후에만 정책 결정 재검증과 출력 검증 역할을 수행한다.

`/proxy/analyze`는 LLM 호출이 없는 사전 분석 API이므로 Validator Agent 출력 재검사는 `SKIPPED`로 기록된다. 이 API는 AI 전송 전 입력 위험도와 마스킹 결과를 미리 확인하기 위한 경로다.

## 검사 항목

- 출력 내 개인정보 잔존 여부: 이메일, 전화번호, 주민등록번호, 계좌번호, 주소 등 기존 PII detector가 지원하는 패턴
- 출력 내 정책 위반 문구: 시스템 프롬프트 노출, 내부 정책 노출, 정책 무시 또는 우회 성공 징후
- 마스킹 누락: 입력 단계에서 `MASK` 처리된 개인정보가 출력에서 다시 등장하는지 확인
- 출력 판단 결과: `ALLOW`, `MASK`, `BLOCK`, `WARN`

## output_action 결정 규칙

| 조건 | output_action |
|---|---|
| 출력에 위험 신호 없음 | `ALLOW` |
| 마스킹 가능한 PII 포함 | `MASK` |
| 주민등록번호, 시스템 프롬프트, 내부 정책, 정책 우회 성공 징후 포함 | `BLOCK` |
| 완전 차단은 아니지만 주의 필요 | `WARN` |

Validator Agent는 LLM 기반 자율 Agent가 아니라 기존 detector, rule, heuristic을 재사용하는 결정적 검증 모듈이다. 따라서 성능 개선 기법처럼 설명하지 않고, "정책 결정 재검증 계층을 운영형 확장으로 분리했다"라고 설명한다.

## final_action 결정 규칙

`input_action`과 `output_action`을 종합해 더 강한 조치를 최종 조치로 사용한다.

```text
BLOCK > MASK > WARN > ALLOW
```

예를 들어 입력은 `MASK`, 출력은 `ALLOW`이면 최종 `final_action`은 `MASK`이다. 입력은 `ALLOW`, 출력은 `BLOCK`이면 최종 `final_action`은 `BLOCK`이다.

## 기존 Output Inspection과의 차이

기존 구조도 출력 탐지를 수행했지만, 이번 변경에서는 이를 명시적인 `ValidatorAgent` 모듈로 분리했다. 따라서 출력 검증 결과는 audit summary와 audit log에 `validator` 필드로 별도 기록되며, `input_action`, `output_action`, `final_action`이 분리된다.

## 한계

- Validator Agent는 규칙 기반 검증 모듈이므로 모든 우회 표현을 탐지하지는 못한다.
- 출력 검증 단계가 추가되어 latency가 증가한다.
- SSE 엔드포인트는 보안 검증을 위해 upstream 응답을 버퍼링한 뒤 Validator Agent 검증 후 안전한 응답만 반환한다. 따라서 이 구현은 실시간 토큰 스트리밍이 아니라 검증 후 일괄 반환 구조에 가깝다.
- 입력 또는 출력이 `BLOCK`이면 원본 응답 token event를 보내지 않는다. 이 보안 경계는 통합 테스트로 확인한다.
- Validator Agent는 본 연구의 핵심 정량 평가 대상이 아니며, 독립 벤치마킹은 후속 연구로 둔다.

## Future Work

향후에는 Validator Agent 적용 전후의 오탐·미탐 변화, 출력 검증 latency, policy consistency 개선 정도를 별도 데이터셋과 실험 설계로 평가한다. 이 평가는 입력 탐지 성능 비교와 분리해서 수행한다. 특히 출력 응답 안에 마스킹 누락, 개인정보 재노출, 시스템 프롬프트 노출, 정책 위반 답변이 포함된 출력 검증 전용 데이터셋이 필요하다.
