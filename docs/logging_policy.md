# Logging Policy

## 목적

이 문서는 보안 프록시에서 어떤 정보는 저장하고, 어떤 정보는 저장하지 않는지 명확히 하기 위한 정책 문서다.

## 저장 대상 (허용)

- `request_id`
- `timestamp_utc`
- `action`
- `reasons`
- `input_action`
- `output_action`
- `pii_detected` / `injection_detected`
- `latency_ms`
- detector count 등 요약 통계

## 저장 금지 대상 (금지)

- 원문 사용자 프롬프트
- 원문 LLM 응답
- API 키/토큰
- 민감정보 원문 (이메일/전화번호/주민번호/계좌번호)

## 점검 절차

1. 응답의 `audit_summary` 필드에 원문 텍스트가 포함되지 않았는지 확인
2. 로그 저장소에 `content` 원문을 기록하지 않도록 점검
3. 릴리즈 전 샘플 요청 5건으로 수동 검증

