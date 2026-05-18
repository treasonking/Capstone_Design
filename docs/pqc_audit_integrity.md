# PQC Audit Integrity

PQC is applied only to audit log integrity protection. It signs the normalized audit record hash to detect post-hoc tampering of security decisions.

## 적용 범위

PQC는 탐지 파이프라인 내부가 아니라 감사 로그 저장 이후의 무결성 보호 계층으로 적용한다.

적용 대상:

- 감사 로그 무결성 보호
- 정책 판정 결과 위변조 방지
- Validator Agent 결과 위변조 방지
- 사고 발생 시 책임 추적과 사후 검증

적용하지 않는 대상:

- PII 탐지 성능 개선
- Prompt Injection 탐지 성능 개선
- Validator Agent 판단 정확도 개선
- LLM 응답 생성
- LLM 요청 암호화
- DB 전체 암호화
- 네트워크 전체 PQC TLS 구현

발표용 문장:

> PQC는 개인정보 탐지나 프롬프트 인젝션 탐지 성능을 향상시키기 위한 기술이 아니라, 탐지 결과와 정책 판정이 기록된 감사 로그의 장기 무결성을 보장하기 위한 보안 확장 요소로 적용한다.

## 서명 구조

```text
감사 로그 JSON 생성
  -> integrity.signature 제외
  -> canonical JSON 생성
  -> SHA-256 해시 생성
  -> PQC-compatible signer로 서명
  -> integrity.signature 저장
  -> 공개 검증 인터페이스로 검증
```

`integrity.signature` 필드 자기 자신은 canonical hash 대상에서 제외한다. 그 외 `input`, `output`, `validator`, `final_action`, `reason_codes` 등 정책 판단 메타데이터는 서명 대상이다.

## 현재 구현

현재 구현은 `backend/app/integrity/pqc_signer.py`의 `MockMLDSASigner`를 사용한다. 이는 개발 및 테스트용 MOCK-ML-DSA signer이며 실제 ML-DSA 구현이 아니다.

운영 환경에서는 같은 인터페이스를 유지하면서 실제 ML-DSA 서명 라이브러리로 교체할 수 있다. ML-KEM은 키 교환용이므로 감사 로그 서명 목적에는 사용하지 않는다.

## 저장 금지 필드

감사 로그에는 다음 원문을 저장하지 않는다.

- raw prompt
- raw response
- API key
- system prompt
- 개인정보 원문

## 검증 방법

```bash
python tools/verify_audit_log.py --log-file logs/audit_log.jsonl
```

검증 도구는 JSONL 각 줄을 읽고 `integrity.signature`를 제외한 canonical hash를 재계산해 서명을 확인한다. `final_action`이나 `reason_codes`가 사후 변경되면 검증이 실패한다.
