# Audit Log Safety

## Goal

감사 로그는 차단 사유를 설명할 수 있어야 하지만, 원문 prompt/response 전문이나 비밀값을 저장해서는 안 된다.

## Stored Fields

- `request_id`
- `user_id`
- `timestamp`
- `action`
- `reason_codes`
- `reason_code`
- `detector_counts`
- `latency_ms`
- `policy_version`
- `model_version`
- `masked_preview`

## Explicitly Excluded

- raw prompt
- raw response
- Authorization header
- API key
- Cookie
- 주민등록번호 원문
- 전화번호 원문
- 계좌번호 원문

## Implementation Notes

- `backend/app/services/proxy_service.py`
  - preview 생성 시 PII를 먼저 마스킹한다.
  - `Authorization: Bearer ...`, `api-key=...`, `Cookie: ...` 패턴을 `[REDACTED]`로 치환한다.
- `backend/app/services/audit_service.py`
  - 안전한 메타데이터만 JSONL로 저장한다.

## Validation

- `backend/tests/test_audit_service.py`
- `backend/tests/test_audit_log_safety.py`

이 테스트들은 전화번호와 Bearer token이 로그 직렬화 결과에 남지 않는지 확인한다.
