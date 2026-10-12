# 사용자 채팅·관리자 재통합

## 범위와 병합

작업 대상은 `wkdnjs5665-login-signup-ui`이다. UI 원격 기준 `bce22d6f562b38d1453c2a29d52125eb3082e653`에 master `a89edc7280919d12242352631e2218b8668b1761`을 병합했다. 공통 조상은 `90910e8`이며 `frontend/demo.html` 충돌을 기능별로 해결했다. UI 경로·TEAM ORCA 브랜딩·가입 성공 안내를 유지하면서 master의 Provider allowlist, 서버 모델 설정, 인증 요청 소유권, 헤더부터 본문까지 15초 timeout, 감사 보호를 유지한다. 되돌려진 SecurityLab은 다시 도입하지 않았다.

원래 master checkout의 수정된 `models/lightweight/classifier.joblib`는 그대로 두고 별도 worktree에서 구현했다. master 직접 푸시와 자동 PR 병합은 수행하지 않는다.

## 화면과 상태

| 경로 | 표시와 접근 |
|---|---|
| `/login` | 이메일·비밀번호, 입력/연결 오류, 회원가입 이동 |
| `/signup` | 이메일·비밀번호·확인, 성공 후 로그인 경로와 이메일·안내 유지. 비밀번호 정리 |
| `/app` | 메모리 내 질문·최종 답변 기록, 전송·재시도·새 대화·로그아웃 |
| `/admin` | 일반 로그인 + 별도 관리자 토큰. 통계·최근 차단·reason_code·Provider 설정·현재 상세 검증 요청 |

History API로 경로를 변경하며 뒤로 가기·페이지 이탈·로그아웃·새 대화는 진행 요청을 무효화한다. 직접 진입과 새로고침은 동일 HTML을 서빙하고 인증 상태를 다시 확인한다. 인증 확인 중에는 보호된 화면을 노출하지 않는다. `/`와 `/demo.html`은 로그인 또는 세션 복원 후 `/app`으로 정규화한다.

대화는 각 질문 단위의 API 호출이다. 이전 메시지를 이어 붙이지 않는다. 새 대화는 **화면 기록 초기화**이며 서버 대화 세션 생성이 아니다. 원문은 메모리·DOM에만 유지되고 localStorage/sessionStorage/DB/감사 로그에 새로 저장하지 않는다. 사용자 Bearer와 인증 origin만 기존 sessionStorage에 저장한다. 가입 이메일은 현재 페이지 메모리에서만 유지한다.

Enter 전송 / Shift+Enter 줄바꿈 / IME 조합 중 Enter 무시 / 빈 입력·중복 제출 방지 / 메시지별 대기·실패 / 실패 질문 snapshot으로 수동 재시도를 제공한다. 모든 질문과 답변은 `textContent`로 표시하며 Markdown/HTML 실행은 지원하지 않는다.

## 요청 흐름

1. 입력 snapshot을 고정하고 `/proxy/analyze` 호출: 모델 호출 없는 사전 검사.
2. BLOCK이면 안내만 표시한다. WARN이면 확인·취소를 제공하며 취소 시 전송하지 않는다.
3. 동일 snapshot으로 `/proxy/chat` 호출: 서버 입력 재검사, 마스킹/차단, Provider 호출, 전체 출력 Validator 검사.
4. 최종 ALLOW/MASK/WARN의 content만 답변으로 표시한다. BLOCK/ERROR의 content는 서버 projection에서 제거하며 UI도 표시하지 않는다.

WARN 확인은 UI의 사용성 절차이며 보안 권한 부여가 아니다. 직접 API 호출에도 서버 재검사·egress 마스킹·BLOCK이 적용된다. 기본 정책의 계좌번호 WARN도 Provider 입력에서는 마스킹된다. MASK 안내는 입력 마스킹과 출력 마스킹을 구분한다.

실패는 AI 답변으로 표시하지 않는다. Provider 원시 오류와 내부 설정은 일반 사용자에게 반환·표시하지 않는다. timeout은 각 HTTP 요청의 헤더와 본문 소비에 적용되며 자동 재전송하지 않는다. 서버 처리가 이미 완료됐을 수 있으므로 수동 재시도에도 중복/비용 위험이 남는다.

## API 계약과 이전 클라이언트 마이그레이션

| 경로 | 일반 사용자 Bearer | 추가로 유효한 X-Admin-Token |
|---|---|---|
| POST `/proxy/analyze` | `{action}` | 기존 상세 ProxyAnalyzeResponse, Validator SKIPPED 구분 유지 |
| POST `/proxy/chat` | `{action, content, input_masked, output_masked}` | 기존 상세 ProxyResponse |
| POST `/proxy/chat/stream` | 접근 거부 | 기존 버퍼링 후 검증 SSE |
| POST 프록시 앱 `/v1/chat/completions` | 접근 거부 | 기존 진단용 Mock 호환 응답 |
| GET `/admin/*` | 접근 거부 | 기존 관리자 집계/설정 응답. API 자체는 관리자 토큰으로 인증 |

기존 상세 응답을 사용하는 클라이언트는 사용자 Bearer에 관리자 헤더를 추가해야 한다. 헤더가 잘못되면 조용히 사용자 응답으로 낮추지 않고 401(관리자 미설정 503)로 거부한다. `debug=true` 등 쿼리/JSON 필드는 상세 응답 권한을 주지 않는다. 프록시 앱의 Mock 호환 경로에도 상세 감사 메타데이터가 있으므로 관리자 인증을 적용했다. 별도 `tools.mock_llm` upstream 서버는 변경하지 않았다.

일반 요청의 `policy_id`, `model`, `user_id`는 서버에서 덮어쓴다. `USER_POLICY_ID=default|strict`만 허용하고 잘못된 설정은 503으로 fail closed한다. 관리자 진단은 기존 allowlist 내 정책 선택을 유지한다. Provider/model은 기존 서버 설정만 따른다.

## 관리자 비동기 보호

집계 조회는 토큰 버전·API origin·사용자 세션·요청 번호를 snapshot으로 캡처한다. 토큰 변경·로그아웃·origin 변경·화면 이동은 기존 요청을 취소하고 늦은 응답을 버린다. timeout은 이전 수치와 Provider 설정을 초기화하고 토큰을 유지하며 재조회 버튼을 복구한다. 상세 검사도 관리자 토큰 변경 시 취소·초기화한다. 이전 사용자 요청의 늦은 401이 새 사용자 세션을 지우지 않게 요청 시점 토큰을 확인한다.

관리자 토큰은 페이지 메모리 외의 저장소·URL·로그에 저장하지 않는다. 현재 상세 검증 결과와 집계 이력은 별개다. 과거 요청 원문·개별 서명 검증 결과·과거 Validator 상세를 조회하는 기능은 만들지 않았다.

## 실행

저장소 루트에서 아래 명령을 각각 별도 터미널로 실행한다. Mock은 별도 8001 서버가 필요하다.

```powershell
$env:LLM_PROVIDER = "mock"
$env:MOCK_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
$env:USER_POLICY_ID = "default"
python -m uvicorn tools.mock_llm:app --host 127.0.0.1 --port 8001
python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
python frontend/dev_server.py
```

UI 기본 5500 / API 기본 8000. `frontend/dev_server.py`는 실행 cwd와 관계없이 frontend를 기준으로 정적 파일을 서빙한다. 알려진 화면 경로와 query/trailing slash만 HTML fallback이며 없는 자산·API는 404다. API를 상대경로로 5500에 보내지 않는다. 공개 설정 `UI_API_ORIGIN`으로 config.js를 생성하며 다른 정적 호스팅에서는 `frontend/config.js`를 설정한다. 키/토큰을 설정 파일에 넣지 않는다.

기존 서버는 임의 종료하지 않는다. 격리 테스트는 `UI_TEST_PORT`, `UI_API_ORIGIN`, `UI_ALLOWED_ORIGINS`, `MOCK_LLM_URL`, 임시 `AUTH_DB_PATH`를 함께 설정하고 직접 생성한 프로세스만 종료한다. 자세한 실행·Docker·평가 절차는 [runbook](demo_runbook.md)에 보존했다.

## 한계

- 계정별 RBAC, 공유 세션 저장소, 실제 멀티턴, 요청 idempotency key는 미구현이다.
- PII 탐지와 프롬프트 인젝션 탐지는 기존 탐지기·정책이며 이번 UI 검증으로 정확도 향상을 주장하지 않는다. 내부/외부 평가 수치는 수정하지 않았다.
- Validator Agent는 출력 생성 후 최종 반환 전 검증이며 SSE도 전체 응답을 버퍼링한다.
- 감사 구조는 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**이다. 실제 ML-DSA와 실제 외부 OpenAI 호출은 검증하지 않았다.
- 운영 배포에는 HTTPS, 비밀 관리, 인증 강화, 요청량 제한, 세션 공유, 데이터 보존·전송 정책 검토가 필요하다.

실제 실행 증거와 미검증 범위는 [검증 보고서](../reports/user_chat_admin_integration_verification.md)를 참고한다.
