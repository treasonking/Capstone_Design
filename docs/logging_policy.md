# Logging Policy

## 목적

이 문서는 보안 프록시에서 어떤 정보는 저장하고, 어떤 정보는 저장하지 않는지 명확히 하기 위한 정책 문서다.

## 저장 대상 (허용)

- `logs/audit_log.jsonl`에는 아래 메타데이터와 요약 정보만 저장한다.
- `request_id`
- `user_id` (비식별 식별자 권장)
- `timestamp_utc`
- `action`
- `reasons`
- `input_action`
- `output_action`
- `pii_detected` / `injection_detected`
- `latency_ms`
- `detector_counts`, `matched_detector_count`, `detectors_invoked` 같은 detector 요약 통계
- `hybrid_detection.model_status`, `fallback_used`, `fallback_reason` 같은 선택형 분류기 상태 메타데이터

## 저장 금지 대상 (금지)

- 원문 사용자 프롬프트
- 원문 LLM 응답
- API 키/토큰
- 민감정보 원문 (이메일/전화번호/주민번호/계좌번호)

`logs/audit_log.jsonl`에는 원문 `prompt`나 원문 `response`를 저장하지 않는다. 감사 로그는 정책 판정, 탐지 여부, 지연 시간 같은 안전한 요약 정보만 남기고 원문 텍스트는 기록하지 않는다.

`detector_counts`는 "이유 코드를 하나 이상 남긴 detector 종류 수"를 요약한 필드다. 예를 들어 regex와 선택형 분류기 경로가 모두 위험 신호를 남기면 `{"regex": 1, "llm": 1}`처럼 기록된다. 반면 `detectors_invoked`는 실제로 실행된 detector 목록이므로, match가 없더라도 실행 사실은 여기에서 확인한다.

## user_id 권장값

- `user_id`에는 실제 이름, 학번, 주민등록번호를 넣지 않는다.
- `anonymous`, `role_id`, `session_hash` 같은 비식별 값을 권장한다.
- 운영 환경에서도 원문 신원값 대신 내부 식별자나 해시 기반 세션 식별자를 사용한다.

## 점검 절차

1. 응답의 `audit_summary` 필드에 원문 텍스트가 포함되지 않았는지 확인
2. `logs/audit_log.jsonl`에 `prompt`, `response`, `content` 원문이 기록되지 않도록 점검
3. 릴리즈 전 샘플 요청 5건으로 수동 검증

