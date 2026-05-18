# Presentation Q&A

## Q1. Precision/Recall/F1이 모두 1.000인데 과적합 아닌가요?

A.
- 맞다. 내부 데이터셋은 한국어 공공기관 업무 시나리오 중심으로 구성되어 있기 때문에 높은 성능이 나올 수 있다.
- 그래서 외부 공개 데이터셋인 `deepset/prompt-injections`, `protectai/prompt-injection-validation`, `Lakera/gandalf_ignore_instructions`를 추가로 적용했고, 영어 기반 공격에서는 Recall이 낮다는 한계를 확인했다.
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
- internal-only baseline에서는 영어 공개 데이터셋에 대한 모델 기여도가 낮았고, 이를 한계로 명시했다.
- 이번 개선에서는 외부 공개 데이터셋을 train/eval로 분리해 external-tuned 경량 모델을 학습했고, held-out eval split에서 Hybrid Recall과 Model Unique TP가 증가했다.
- 실제 운영 수준으로 확장하려면 영어 데이터셋 기반 재학습을 계속하되, hard negative 보강과 threshold calibration을 함께 해야 한다.

## Q10. Hybrid가 Rule Only보다 좋은 근거가 있나요?

A.
- 최종 평가에서는 외부 공개 데이터셋 3종에 대해 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리하여 Precision, Recall, F1, Accuracy, latency를 비교했다.
- internal-only baseline에서는 `deepset`과 `protectai`에서 Rule Only와 Hybrid가 거의 같았고, `Lakera`에서만 소폭 개선됐다.
- external-tuned 모델은 held-out eval split 기준 Hybrid Recall을 `deepset=0.2278`, `protectai=0.7392`, `Lakera=0.9500`까지 올렸다.
- 따라서 답변은 "Hybrid가 항상 자동으로 좋아진다"가 아니라, "모델 계층이 Rule miss를 추가 탐지할 때 Hybrid가 좋아지며, 이번 external-tuned 결과에서는 그 기여가 overlap 분석으로 확인됐다"가 정확하다.

## Q11. 모델 artifact가 없으면 하이브리드라고 볼 수 있나요?

A.
- 모델 artifact가 없는 실행 환경에서는 rule fallback으로 동작한다.
- 이는 시스템 중단을 방지하기 위한 안정성 설계이다.
- 다만 평가 보고서에서는 `model_status`를 `enabled`, `artifact_missing`, `dependency_missing` 등으로 분리하여 해석한다.
- 이번 외부 3종 재평가에서는 `vectorizer.joblib`와 `classifier.joblib`가 모두 로드되어 `model_status=enabled`였다.

## Q12. 이 프로젝트는 범용 Prompt Injection 탐지기인가요?

A.
- 아니다. 본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.
- 외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다.
- 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.

## Q13. 실제 PQC를 구현한 건가요?

A.
- 실제 ML-DSA 라이브러리를 직접 탑재한 것은 아니다.
- 현재 구현은 ML-DSA 교체가 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조이다.
- `MOCK-ML-DSA` signer는 내부적으로 HMAC-SHA256을 사용하며, 발표에서는 "PQC를 직접 구현했다"가 아니라 "운영 환경에서 ML-DSA로 교체 가능한 감사 로그 무결성 검증 구조를 구현했다"라고 설명한다.

## Q14. `/proxy/analyze`에는 왜 Validator Agent가 실행되지 않나요?

A.
- `/proxy/analyze`는 LLM 호출이 없는 사전 분석 API이다.
- Validator Agent는 LLM 응답 생성 이후의 출력 검증 계층이므로, analyze 경로에서는 출력 재검사가 `SKIPPED`로 기록된다.
- 이 API는 AI 전송 전 입력 위험도와 마스킹 결과를 미리 확인하기 위한 용도다.

## Q15. SSE 스트리밍은 실시간 토큰 스트리밍인가요?

A.
- 아니다. 보안 검증을 위해 upstream 응답을 먼저 버퍼링한다.
- 이후 Validator Agent가 전체 출력 검사를 수행하고, 안전한 응답만 SSE 이벤트로 반환한다.
- 따라서 현재 구현은 실시간 토큰 스트리밍이 아니라 검증 후 일괄 반환 구조에 가깝다.

## Q16. Rule Only와 Hybrid 성능이 거의 같은데, Hybrid 구조가 의미 있나요?

A.
- Hybrid 구조가 의미 있으려면 모델 계층이 Rule 계층이 놓친 샘플을 추가로 탐지해야 한다.
- internal-only baseline에서는 경량 모델이 영어 공격 표현을 충분히 일반화하지 못해 Rule Only와 Hybrid 성능이 유사했다.
- held-out eval split 기준 internal-only `Model Only Unique TP`는 `deepset=0`, `protectai=0`, `Lakera=6`이었다.
- external-tuned 모델에서는 같은 eval split에서 `Model Only Unique TP`가 `deepset=11`, `protectai=211`, `Lakera=156`으로 증가했다.
- 즉, Hybrid 구조 자체가 불필요했던 것이 아니라, 기존 모델 학습 데이터가 영어 공개 데이터셋에 맞지 않았던 것이다. 외부 데이터 기반 재학습과 threshold optimizer를 통해 모델 계층의 독립 기여도를 늘릴 수 있음을 확인했다.
