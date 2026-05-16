# Presentation Q&A

## Q1. Precision/Recall/F1이 모두 1.000인데 과적합 아닌가요?

A.
- 맞다. 내부 데이터셋은 한국어 공공기관 업무 시나리오 중심으로 구성되어 있기 때문에 높은 성능이 나올 수 있다.
- 그래서 외부 공개 데이터셋인 `deepset/prompt-injections`를 추가로 적용했고, 영어 기반 공격에서는 Recall이 낮다는 한계를 확인했다.
- 본 프로젝트는 이 결과를 숨기지 않고 한계와 개선 과제로 명시했다.

## Q2. 왜 false positive가 0개인가요?

A.
- 내부 평가셋이 현재 규칙 설계와 밀접하게 맞물려 있기 때문이다.
- 그래서 FP 0개를 일반화 성능으로 해석하지 않고, 현재 규칙 변경이 기존 기대 동작을 깨지 않았는지 확인하는 지표로 해석한다.
- 이를 보완하기 위해 `evaluation/external_validation_sample.json` 같은 외부 스타일 샘플 초안을 추가했다.

## Q3. 프론트엔드가 구현되지 않은 것 아닌가요?

A.
- 맞다. 현재 저장소의 핵심 구현 범위는 백엔드 프록시, 정책 엔진, 감사 로그, 관리자 API, 평가 코드다.
- `frontend/`는 placeholder 상태이며, 실사용 UI는 아직 구현되지 않았다.
- 발표/시연은 curl, Swagger UI, 평가 리포트, 관리자 API 응답을 중심으로 진행한다.

## Q4. 관리자 API는 어떻게 보호하나요?

A.
- `/admin/stats`, `/admin/recent-blocks`, `/admin/reason-codes`, `/admin/upstream-config`는 `X-Admin-Token` 헤더 기반 인증을 사용한다.
- 토큰은 `ADMIN_API_TOKEN` 환경변수에서 읽고, 미설정 시 개발 기본값 `dev-admin-token`을 사용한다.
- 사용자 프록시 엔드포인트 `/proxy/chat`, `/v1/chat/completions`에는 이 인증을 적용하지 않는다.

## Q5. strict policy는 무엇이 다른가요?

A.
- 기본 정책은 `policies/policy.yaml`, 강화 정책은 `policies/strict.yaml`이다.
- 요청의 `policy_id`가 `default`이면 기본 정책, `strict`이면 강화 정책을 사용한다.
- 허용되지 않은 `policy_id`는 400으로 거부하고, path traversal 방지를 위해 영문/숫자/`_`/`-`만 허용한다.

## Q6. 감사 로그에 원문 prompt/response가 저장되나요?

A.
- 저장하지 않는다.
- `logs/audit_log.jsonl`에는 `request_id`, `timestamp`, `action`, `reason_codes`, 탐지 여부, 지연 시간 같은 요약 정보만 저장한다.
- `user_id`도 실제 이름이나 학번 대신 `anonymous`, `role_id`, `session_hash` 같은 비식별 값을 쓰는 것을 권장한다.

## Q7. 실제 LLM 연동도 가능한가요, 아니면 mock만 되나요?

A.
- 현재 MVP는 `mock`, `openai`, `azure`, `ollama` 경로를 모두 고려한 구조를 갖고 있다.
- 발표/시연에서는 재현성을 위해 주로 mock upstream을 사용한다.
- 실제 upstream을 사용할 때는 OpenAI/Azure 설정 누락을 호출 전에 검사하고, 오류는 `UPSTREAM_CONFIG_ERROR`로 분리해 반환한다.

## Q8. Python 3.12.3 환경에서도 설치 가능한가요?

A.
- 패키지 메타데이터의 Python 지원 범위를 `>=3.10,<3.13`으로 조정해 3.12 계열 설치 실패를 막았다.
- README도 3.10~3.12 지원으로 정리했다.
- 발표 시에는 "현재 저장소 설정상 3.12를 허용하도록 수정했고, 실제 시연 환경 검증은 별도 Python 3.12 인터프리터에서 다시 확인한다"라고 답변하면 된다.

## Q9. 영어 Prompt Injection에 약하면 실제로 쓸 수 있나요?

A.
- 현재 버전은 범용 글로벌 Prompt Injection 탐지기가 아니라 한국어 공공기관·사내망 환경을 우선 대상으로 한 PoC이다.
- 영어·혼합언어 공격 패턴은 현재 개선 과제로 식별했고, 일부 대표 패턴은 룰에 추가했다.
- 실제 운영 수준으로 확장하려면 영어 데이터셋 기반 재학습과 threshold 조정이 필요하다.

## Q10. Hybrid가 Rule Only보다 좋은 근거가 있나요?

A.
- 최종 평가에서는 Rule Only, Lightweight Model Only, Hybrid를 분리하여 Precision, Recall, F1, latency를 비교했다.
- 이를 통해 규칙 기반 탐지의 안정성과 경량 모델 기반 탐지의 보완 가능성을 비교했다.
- 단, 모델 artifact가 없는 fallback 상태는 별도로 표시하여 완전한 Hybrid 성능으로 과장하지 않았다.

## Q11. 모델 artifact가 없으면 하이브리드라고 볼 수 있나요?

A.
- 모델 artifact가 없는 실행 환경에서는 rule fallback으로 동작한다.
- 이는 시스템 중단을 방지하기 위한 안정성 설계이다.
- 다만 평가 보고서에서는 `model_status`를 `loaded` 또는 `artifact_missing`으로 분리하여 해석한다.

## Q12. 이 프로젝트는 범용 Prompt Injection 탐지기인가요?

A.
- 아니다. 본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.
- 외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다.
- 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.
