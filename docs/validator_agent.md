# Validator Agent

Validator Agent is an output validation layer that checks LLM-generated responses after generation and before returning them to the user.

## 정의

Validator Agent는 LLM 또는 Mock LLM이 생성한 출력값을 최종 사용자에게 반환하기 전에 검사하는 정책 기반 보안 검증 계층이다. 입력 단계에서 탐지되지 않았거나, LLM 응답 과정에서 새롭게 생성된 개인정보, 정책 위반 응답, 마스킹 누락을 재검사한다.

발표용 문장:

> Validator Agent는 LLM 응답 생성 이후 최종 사용자 반환 이전 단계에 배치하여, 출력 내 개인정보 잔존 여부와 정책 위반 응답을 재검사하는 출력 검증 계층이다.

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

Validator Agent는 입력 검사 전에 실행하지 않는다. 입력 탐지는 기존 detector와 policy engine이 수행하고, Validator Agent는 LLM 응답 생성 이후에만 출력 검증 역할을 수행한다.

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

Validator Agent는 LLM 기반 자율 Agent가 아니라 기존 detector, rule, heuristic을 재사용하는 결정적 검증 모듈이다.

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
- 스트리밍 응답은 최종 검증 전 사용자에게 unsafe token이 전달되지 않도록 버퍼링 후 검증된 내용을 반환한다.
