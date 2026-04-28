# Policy Guide

## 목적

이 문서는 `policies/policy.yaml` 기준으로 reason code, 우선순위, threshold, 마스킹 규칙을 빠르게 확인하기 위한 운영 가이드다.
각 reason_code의 세부 정의와 legacy alias 관계는 `docs/reason_codes.md`를 참고한다.

## Reason Codes

### PII

- `PII_EMAIL_DETECTED`: 이메일 주소 패턴 탐지
- `PII_PHONE_DETECTED`: 휴대전화(하이픈/공백/국가코드 포함) 패턴 탐지
- `PII_ADDRESS_DETECTED`: 한국 주소 상세 표기(시/군/구 + 도로명/동명 + 번지) 탐지
- `PII_RRN_DETECTED`: 주민등록번호 형식 탐지
- `PII_ACCOUNT_DETECTED`: 계좌번호 유사 패턴 탐지

### Prompt Injection

- `INJ_IGNORE_PREVIOUS_INSTRUCTIONS`: 이전 지시 무시 유도
- `INJ_REVEAL_SYSTEM_PROMPT`: 시스템 프롬프트/시스템 지시문 공개 요구
- `INJ_POLICY_BYPASS_ATTEMPT`: 정책 우회, jailbreak, developer mode 유도
- `INJ_DIRECT_OVERRIDE_ATTEMPT`: 이전/상위 지시 또는 정책 무시 요구
- `INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT`: hidden instruction/system prompt 추출 시도
- `INJ_RULE_DISCLOSURE_ATTEMPT`: 내부 규칙, 응답 기준, 정책 목록 공개 요구
- `INJ_ROLE_OVERRIDE_ATTEMPT`: 역할 재정의로 우회 유도
- `INJ_DEBUG_MODE_ATTEMPT`: 디버그/개발자/관리자 모드 전환 유도
- `INJ_MULTI_STEP_EXTRACTION_ATTEMPT`: 단계적 내부 기준 추출 시도
- `INJ_OBFUSCATED_INJECTION_ATTEMPT`: 난독화된 prompt injection 시도
- `SAFE_INPUT`: 위험 신호 미탐지

## 정책 우선순위 / Threshold

- 우선순위는 `priority`가 클수록 우선 적용한다.
- 같은 점수대에서 더 강한 액션(`BLOCK > MASK > WARN > ALLOW`)을 우선한다.
- `threshold`는 탐지 score가 임계치 이상일 때만 룰을 적용한다.

현재 기본 정책 예시:

- 이메일/전화번호/주소: `MASK`
- 주민등록번호: `BLOCK`
- 계좌 유사 패턴: `WARN`
- Injection 주요 패턴: `BLOCK`

## 마스킹 고정 규칙

- 이메일: `ab***@domain.com`
- 휴대전화: `010-12**-****`
- 주민등록번호: `900101-1******`
- 계좌번호: 앞 2자리/뒤 2자리 노출, 중간 마스킹 (`12******34`)

## 운영 주의사항

- 감사 로그에는 `reason_code`, `action`, `request_id`, 요약 정보만 저장한다.
- 원문 prompt/response 및 민감정보 원문은 저장하지 않는다.
