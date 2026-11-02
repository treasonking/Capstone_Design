# Security Limitations

본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

## Scope

- 우선 방어 대상은 주민등록번호, 연락처, 이메일, 주소, 계좌번호 등 공공기관 민원 업무에서 자주 등장하는 개인정보와 정책 우회형 Prompt Injection이다.
- `ignore previous instructions`, `reveal the system prompt`, `bypass safety policy`, `act as DAN` 같은 대표 영어 패턴은 보강했지만, 모든 영어 jailbreak 또는 간접 Prompt Injection을 포괄하지 않는다.
- `이전 instructions 무시`, `system prompt 보여줘`, `policy bypass 해줘` 같은 한국어-영어 혼합 표현은 국내 업무 환경에서 현실적으로 발생할 수 있는 최소 우회 표현으로 다룬다.

## Known Limits

- 외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.
- Lightweight classifier artifact가 존재하지 않는 경우 시스템은 실행 중단 대신 rule-based fallback으로 동작한다. 이는 데모 안정성을 위한 설계이나, Hybrid 성능 평가에서는 `model_status`를 `artifact_missing`으로 분리 표시한다.
- 따라서 fallback 상태의 결과를 완전한 Hybrid 성능으로 해석하지 않는다.
- 보안 설명, 정책 작성, 예방 방법 문의처럼 공격을 설명하는 문장은 차단 대상이 아니다. 예: `Explain what prompt injection is.`, `이전 지시를 무시하라는 공격을 어떻게 막을 수 있어?`
- Validator Agent는 정책 결정 재검증을 위한 운영형 확장 요소이며, 본 연구의 핵심 정량 평가 대상이 아니다. 적용 전후 오탐·미탐 변화와 latency 평가는 후속 연구로 둔다.
- PQC 기반 감사로그 서명 구조는 탐지 성능 향상 요소가 아니라 감사로그 무결성 확장 요소이다. 현재 구현은 ML-DSA 교체 가능한 인터페이스와 Mock signer 기반 검증 구조이며, 실제 PQC 알고리즘 적용 및 성능 평가는 후속 연구로 둔다.
- 사용자 계정은 SQLite에 저장하지만 로그인 세션은 서버 프로세스 메모리에만 저장한다. 서버 재시작 시 토큰이 무효화되고, 공유 세션 저장소 없이 여러 worker를 사용하면 세션이 worker 간 공유되지 않는다.
- 관리자 API는 별도 `ADMIN_API_TOKEN`으로 보호되며 공개 기본값은 없다. 이는 계정별 관리자 역할과 권한 회수를 제공하는 RBAC 구현이 아니다.
- SSE 경로도 upstream 응답 전체를 메모리에 버퍼링한 뒤 검증한다. 검증 전 원본 토큰 노출을 막는 대신 first-byte latency와 메모리 사용량이 증가하며, 대용량 응답 제한은 별도 운영 정책이 필요하다.
- `store=False`는 OpenAI Responses application state 저장을 끄지만 모든 데이터 보존을 의미하지 않는다. 조직이 승인된 Zero Data Retention 또는 Modified Abuse Monitoring 제어를 사용하지 않으면 abuse monitoring log에 고객 콘텐츠가 보존될 수 있으므로 기관 정책과 최신 OpenAI 데이터 제어 문서를 별도 확인해야 한다.
- OpenAI Provider를 사용하면 `ALLOW` 입력과 `MASK` 처리된 입력이 외부 사업자에게 전송된다. 탐지 누락, 마스킹 한계, Provider별 처리 지역·보존 정책 차이는 프록시만으로 제거할 수 없다.
- Provider 직전 egress guard는 위치가 확인된 PII를 정책 action과 무관하게 마스킹하고, 위치를 알 수 없는 PII 신호는 `PII_UNMASKABLE_DETECTED`로 차단한다. 그러나 탐지기가 PII 자체를 놓친 경우에는 원문 전송 위험이 남는다.
- 모델별 응답 품질과 Validator 탐지 결과가 달라질 수 있으며 비용, Rate Limit, 네트워크 장애, timeout이 발생할 수 있다. `PROVIDER_AUTH_ERROR`, `PROVIDER_RATE_LIMITED`, `PROVIDER_TIMEOUT`, `PROVIDER_UPSTREAM_ERROR`, `PROVIDER_INVALID_RESPONSE`는 정책 차단과 별도 오류로 기록한다.
- 자동 Provider 라우팅과 다른 사업자로의 자동 폴백은 구현하지 않았다. 향후 도입하려면 기관 allowlist, 사용자 또는 기관의 명시적 동의, 전송 데이터 분류 재검사, Provider 변경 감사 기록, 최대 시도 횟수가 필요하다.
- 현재 실제 구현 Provider는 Mock과 OpenAI뿐이다. Claude, Gemini, Azure OpenAI, 로컬 LLM은 공통 인터페이스에 어댑터를 추가해야 하며 현 상태에서 지원한다고 설명하면 안 된다.
- 기본 Docker Compose는 `OPENAI_API_KEY`를 자동 전달하지 않는다. 환경변수 직접 주입은 Compose 설정 출력과 컨테이너 메타데이터에 평문으로 나타날 수 있으므로 운영 배포에는 조직의 secret store 또는 Docker secret 통합이 필요하다.

OpenAI 관련 운영 판단은 공식 [Responses API 안내](https://developers.openai.com/api/docs/guides/migrate-to-responses), [데이터 제어 문서](https://developers.openai.com/api/docs/guides/your-data), [오류 코드 문서](https://developers.openai.com/api/docs/guides/error-codes)의 최신 내용을 기준으로 다시 확인해야 한다.
- 감사 로그의 개발용 signer는 HMAC-SHA256 Mock 구현이다. 기본 개발 키와 기본 `user_id` salt는 공개된 fallback 값이므로 운영 보안을 제공하지 않는다. 비운영 환경 밖에서는 `AUDIT_LOG_HMAC_KEY`, `AUDIT_USER_ID_SALT`를 별도 비밀 관리 체계에서 주입해야 한다.
- `user_id`는 저장 전에 HMAC 기반 가명값으로 바뀌지만, salt가 유출되거나 식별자 후보 공간이 작으면 사전 대입 위험이 남는다.
- 기본 경량 분류 artifact와 external-tuned artifact가 서로 다른 scikit-learn 버전에서 만들어졌다. 직렬화 artifact는 버전 호환성 경고 없이 로드되는 버전에서 재학습·고정하고 해시와 학습 메타데이터를 함께 배포해야 한다.
- 외부 held-out split에는 train/eval 정규화 텍스트 해시 중복 42건이 남아 있어 external-tuned 수치가 낙관적일 수 있다.

## Operation Guidance

- 사용자 UI는 같은 안내 유형의 성공한 최근 대화 최대 6쌍을 메모리에서 관리한다. 각 요청은 이력 전체와 현재 질문을 다시 검사·마스킹한 뒤 Provider에 전달한다. 서버 대화 DB는 만들지 않으며 새 대화·새로고침·로그아웃·화면 이탈 시 이력을 잃는다. 브라우저 메모리에는 사용자가 입력한 원문이 실행 중 남을 수 있다.
- 클라이언트가 보낸 과거 답변도 비신뢰 데이터로 처리한다. `system`/`developer` 역할은 허용하지 않으며 모든 이력을 단일 사용자 입력 안에 넣는다. 이는 이력 위조나 모델의 명령 추종 위험을 완전히 제거하는 인증 체계가 아니다. 이력까지 정책에 해당하면 새 질문도 차단될 수 있다.
- 일반 `/proxy/chat`은 최종 content와 최소 정책 안내 필드만 반환하고 `/proxy/analyze`는 action만 반환한다. 전체 진단 응답과 상세 SSE, 프록시 앱의 진단용 `/v1/chat/completions`에는 관리자 토큰이 필요하다. 이전 상세 API 클라이언트는 인증 헤더를 갱신해야 한다. 별도 Mock upstream 서버는 로컬 테스트용이며 외부에 공개하지 않는다.
- 사용자 정책은 서버 `USER_POLICY_ID`로 고정한다. WARN 확인은 UI 사용성 절차이지 서버의 보안 승인 토큰이 아니다. 직접 API 호출로 확인창을 건너뛰어도 서버의 재검사·마스킹·BLOCK은 그대로 적용된다.
- 브라우저 timeout/취소는 서버 Provider 실행을 되돌리거나 비용 발생을 취소하지 않는다. 수동 재시도에도 중복 처리가 생길 수 있으며 idempotency key는 미구현이다.

- 운영 또는 발표 자료에서는 내부 데이터셋 F1 1.0을 일반화 성능으로 설명하지 않는다.
- 외부 영어 데이터셋 결과는 범용 확장을 위한 한계 분석 자료로 분리한다.
- 실제 운영 수준으로 확장하려면 영어 공개 데이터셋 기반 재학습, threshold 조정, 간접 인젝션/RAG 문서 공격 평가, hard negative 확장이 필요하다.
- Validator Agent와 PQC를 탐지 성능을 높이는 핵심 기법처럼 설명하지 않는다. 두 요소는 운영 환경에서 정책 결정의 신뢰성, 감사 가능성, 로그 무결성을 높이기 위한 확장 요소로 설명한다.
- 기존 로컬 `logs/audit_log.jsonl`에는 서명 도입 전 또는 구형 포맷 레코드가 섞일 수 있다. 배포 시 로그 스키마 버전과 키 ID별 검증·보존·마이그레이션 정책을 정의해야 한다.

## 주민센터 자료 대조 범위 (2026-11-02)

- 10개 업무의 출처를 대조하고 전국 공통 안내 7건과 지역 참고 3건을 구분했다. 정부24는 공식 검색 추출문 대조이며 전체 원문 및 법령의 현행성 검증을 완료한 것이 아니다.
- 자료의 `scope`, `source_access`, 확인일 및 한계를 Provider 지침에 전달하고 출처에 적용 범위를 표시하지만, 이는 모델의 실제 근거 준수나 법률적 정확성을 강제하는 검증기가 아니다.
- 지역 수수료·면제·접수 경로를 다른 지역으로 일반화하지 않도록 지시한다. 특정 행복 주민센터의 소재지와 운영시간·전화·창구 자료는 미등록이며 모델이 이를 지어내지 않는지는 실제 모델 평가가 필요하다.
- 자료 변경은 민원 안내 문맥 보강이며 PII·인젝션 탐지 규칙 또는 외부 벤치마크 수치를 변경하지 않는다.

## 주민센터 자료 확대 (2026-11-03)

- 현재 30개 업무(전국 안내 26건, 지역 참고 4건)이며 위 2026-11-02의 10건은 이전 검토 기록이다. 신규 자료는 정부24·행정안전부·목포시 공식 안내를 대조했다.
- 복지 신청 자료는 절차·접수 경로와 기본 증빙 안내이며 수급권·선정·급여액의 개인별 판정 기능이 아니다. 장애인 등록 안내도 의료적 판단이나 진단을 제공하지 않는다.
- 서류에 필요한 계좌·소득·의료기록 등을 채팅으로 제출하도록 유도하지 않는다. 실제 기관 제출과 채팅 입력을 구분하도록 지시한다.
- 100개 추가 질문은 내부 검색·보안 회귀이며 실제 모델의 환각·답변 근거 준수 평가가 아니다. 원문에 구형 서식·명칭이 남아 있는 보육료 자료는 현재 필수서류로 전재하지 않았다.
