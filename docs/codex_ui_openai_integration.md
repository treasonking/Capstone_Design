# UI·OpenAI 보안 통합 구조

## 적용 범위와 이력

이 통합은 최신 UI 브랜치 `wkdnjs5665-login-signup-ui`의 `90910e8`을 기준으로 보안 수정 `fd09902`와 OpenAI Provider 어댑터 `5e20a76`을 순서대로 적용했다. 충돌은 인증·CORS·관리자 UI를 보존하면서 `LLM_PROVIDER=mock|openai` Registry 구조가 우선하도록 해결했다.

통합 브랜치는 `codex/ui-openai-integration`이며 `master`를 직접 수정하거나 자동 병합하지 않는다. 원본 커밋은 cherry-pick의 `-x` 메타데이터로 추적한다.

## 요청 처리 경계

```text
브라우저 UI
  -> Bearer 인증 및 origin 고정
  -> PII·Prompt Injection 입력 탐지
  -> 정책 ALLOW/MASK/WARN/BLOCK
  -> 서버 환경변수로 고정된 Provider 선택
  -> Mock 또는 OpenAI Responses API
  -> 전체 응답 버퍼링
  -> Validator Agent 출력 검증
  -> 최종 정책·응답·감사 메타데이터
```

- `BLOCK` 입력은 Provider를 호출하지 않는다.
- `MASK`와 마스킹 가능한 `WARN` 입력은 원문 대신 안전하게 변환된 입력만 Provider에 전달한다.
- Validator Agent는 Mock 또는 OpenAI 응답 생성 이후 최종 반환 전의 출력 검증 계층이다.
- SSE도 검증 전 토큰을 내보내지 않고 전체 응답을 버퍼링한 뒤 결과를 반환한다. 실시간 토큰 스트리밍 검증으로 표현하지 않는다.
- `/proxy/analyze`는 LLM 호출이 없는 사전 분석 API이므로 출력 검증은 `SKIPPED`일 수 있다.

## OpenAI Provider

Provider Registry는 `mock`, `openai`만 허용한다. 요청 본문의 `model`이나 URL로 Provider를 바꿀 수 없으며 Azure OpenAI, Ollama, Claude, Gemini와 자동 폴백은 구현하지 않았다.

OpenAI 경로는 서버에서만 다음 값을 읽는다.

| 환경변수 | 역할 |
|---|---|
| `LLM_PROVIDER=openai` | OpenAI Provider 명시 선택 |
| `OPENAI_API_KEY` | 서버 전용 API 키. UI·응답·감사 로그에 노출하지 않음 |
| `OPENAI_MODEL` | 프로젝트에서 실제 사용 가능한 모델 ID |
| `OPENAI_TIMEOUT_SECONDS` | 요청 timeout |
| `OPENAI_MAX_OUTPUT_TOKENS` | 출력 토큰 상한 |

어댑터는 공식 SDK의 `AsyncOpenAI.responses.create`를 사용한다. Provider로 넘어가는 값은 정책 처리된 `safe_input`이며 `store=False`, timeout, 출력 상한을 명시하고 SDK 자동 재시도는 `max_retries=0`으로 비활성화한다. Responses API는 `store`를 생략하면 저장이 기본값이므로 이 설정을 유지한다. 공식 근거는 [Responses API 전환 가이드](https://developers.openai.com/api/docs/guides/migrate-to-responses), [Responses 생성 API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create), [데이터 제어](https://developers.openai.com/api/docs/guides/your-data)를 따른다.

`store=False`는 모든 형태의 데이터 보존이 사라진다는 뜻이 아니다. 실제 배포 전 OpenAI 조직의 데이터 제어, abuse monitoring 조건, 기관 개인정보 처리 기준과 모델 사용 권한을 별도로 확인해야 한다.

## 감사 로그와 무결성

- 감사 로그에는 provider, model, 호출 여부, 상태, latency, 정책 결정과 탐지 건수 같은 최소 메타데이터만 남긴다.
- raw prompt, raw response, API key, Authorization header, system prompt, 개인정보 원문과 SDK 오류 객체는 저장하지 않는다.
- `user_id`는 `AUDIT_USER_ID_SALT`를 사용한 HMAC 기반 가명값으로 기록한다.
- 중첩 summary도 재귀적으로 정리한다.
- 감사 로그 서명은 `AUDIT_LOG_HMAC_KEY`를 사용하는 개발용 `HMAC-SHA256-MOCK`, `MOCK_ONLY` 구현이다.
- 현재 상태는 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**이며 실제 PQC 또는 ML-DSA 구현이 아니다.

## UI 비동기 안전성

| 결함 | 적용 내용 | 실행 검증 |
|---|---|---|
| UI-01 관리자 stale 응답 | 관리자 전용 AbortController·요청 세대·토큰 버전·사용자 세션·origin snapshot을 캡처하고 성공·실패·finally 모두 최신 요청일 때만 DOM을 갱신 | 토큰 변경, 로그아웃, origin 변경, 사용자 세션 변경 뒤 지연 응답이 통계 재표시를 못함 |
| UI-02 인증 모드 경합 | 요청 시작 시 mode/origin/email/password snapshot을 고정하고 입력·탭·전환 버튼을 잠금. 응답의 `access_token`을 검증하고 지연 화면 전환도 세대로 무효화 | 회원가입 응답 대기 중 로그인 탭 전환 시도, 누락 토큰, 지연 전환 취소 검증 |
| UI-03 body timeout 누락 | timeout을 response header 수신이 아니라 `response.text()`와 JSON 처리 완료까지 유지 | header 지연, body 지연·실패, caller abort, 비JSON, 204 응답 검증 |
| UI-04 timeout 후 잠금 유지 | 인증·세션 복원·관리자 요청에서 작업 소유권과 성공 응답 적용 가능성을 분리. timeout으로 controller가 abort되어도 현재 작업의 오류 표시와 정리는 수행하고, 취소된 요청의 늦은 성공은 적용하지 않음 | 로그인·회원가입·세션 복원·관리자 timeout 후 상태 복구와 재시도, 새 요청 뒤 이전 success/failure/finally 차단 검증 |

`ownsAuthRequest`와 `ownsAdminRequest`는 요청 세대, 현재 controller, origin·토큰·세션 snapshot을 기준으로 현재 작업의 정리 권한을 판단한다. timeout이 발생해 `signal.aborted`가 되더라도 동일 작업의 `catch`는 오류 안내를 표시하고 `finally`는 입력·탭·버튼과 controller를 복구한다. 반대로 `canApplyAuthSuccess`와 `canApplyAdminSuccess`는 ownership에 더해 signal이 중단되지 않았는지 확인하므로, 취소를 무시하고 늦게 도착한 성공 응답은 토큰·화면·관리자 통계를 변경하지 못한다.

`/auth/me` timeout은 401 세션 만료와 구분한다. timeout이나 네트워크 확인 실패에서는 저장 토큰을 유지하고 재확인을 안내하지만, 401일 때만 로컬 인증을 제거한다. 회원가입 timeout은 서버가 이미 가입을 완료했을 가능성이 있으므로 실패로 단정하지 않으며, 동일 이메일의 409 안내 후 로그인으로 전환할 수 있다.

모바일에서는 grid 자식의 최소 너비 전파를 차단했다. 390px viewport에서 문서 `scrollWidth`와 `clientWidth`가 모두 375px로 확인되어 수평 오버플로가 없다.

## 실행

Mock 기본 경로:

```powershell
$env:LLM_PROVIDER = "mock"
$env:MOCK_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
```

OpenAI opt-in 경로:

```powershell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "<secret-from-your-secret-manager>"
$env:OPENAI_MODEL = "<available-model-id>"
$env:OPENAI_TIMEOUT_SECONDS = "30"
$env:OPENAI_MAX_OUTPUT_TOKENS = "1000"
.\scripts\run_proxy_openai.ps1
```

실제 OpenAI smoke는 `RUN_LIVE_OPENAI_TESTS=1`과 별도 키·모델·비용 승인이 모두 있을 때만 실행한다. 이번 통합에서는 실행하지 않았다.

## 구현·Mock·미검증 구분

| 구분 | 상태 |
|---|---|
| 인증, UI/API 연결, PII·인젝션 입력 정책, Validator 출력 검증 | 구현 및 자동·로컬 브라우저 검증 |
| Mock Provider | 로컬 HTTP 경로 검증 |
| OpenAI Provider | 공식 SDK fake client와 통합 Stub으로 검증 |
| 실제 OpenAI API | 미검증. 키·모델·비용 승인이 없어 호출하지 않음 |
| Azure OpenAI·Ollama·기타 Provider, 자동 폴백 | 미구현 |
| 감사 로그 서명 | Mock signer 검증 구조. 실제 ML-DSA 아님 |
| 외부 데이터셋 성능 | 기존 평가 산출물과 이번 재실행 결과를 별도 유지. Provider 통합 성능으로 해석하지 않음 |
