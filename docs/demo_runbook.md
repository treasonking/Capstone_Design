# UI/API 데모 실행 가이드

## 1. 환경 준비

저장소 루트에서 개발 의존성을 설치한다.

```powershell
python -m pip install -e ".[dev,perf]"
```

로컬 데모용 환경변수를 설정한다. 아래 값은 예시이며 저장소에 실제 토큰이나 외부 LLM 키를 커밋하지 않는다.

```powershell
$env:ADMIN_API_TOKEN = "replace-with-a-local-demo-token"
$env:AUTH_DB_PATH = "backend/data/auth.sqlite3"
$env:UI_ALLOWED_ORIGINS = "http://127.0.0.1:5500,http://localhost:5500"
$env:UPSTREAM_LLM_PROVIDER = "mock"
$env:MOCK_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
```

`ADMIN_API_TOKEN`을 설정하지 않으면 사용자 인증과 프록시는 사용할 수 있지만 모든 관리자 API는 503으로 거부된다. 공개 기본 관리자 토큰은 없다.

## 2. 서버 실행

터미널 1에서 로컬 Mock LLM을 실행한다.

```powershell
python -m uvicorn tools.mock_llm:app --host 127.0.0.1 --port 8001
```

터미널 2에서 프록시를 실행한다.

```powershell
python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
```

터미널 3에서 정적 UI를 실행한다.

```powershell
python frontend/dev_server.py
```

브라우저에서 `http://127.0.0.1:5500/login`을 연다. 사용자 화면은 `/login`, `/signup`, `/app`, 관리자 화면은 `/admin` 경로를 사용한다. 다른 UI origin을 사용하면 그 origin을 `UI_ALLOWED_ORIGINS`에 쉼표로 구분해 추가하고 프록시를 다시 시작한다.

## 3. 회원가입과 로그인

1. 로그인 화면에서 API Base URL이 `http://127.0.0.1:8000`인지 확인한다.
2. 회원가입 탭에서 이메일과 8자 이상의 비밀번호를 입력한다.
3. 가입 완료 안내 후 로그인한다.
4. 새로고침해 `/auth/me` 기반 세션 복원을 확인한다.
5. 로그아웃 후 입력, 결과, 관리자 토큰이 지워졌는지 확인한다.

계정은 SQLite에 남지만 Bearer 세션은 프록시 프로세스 메모리에만 있다. 서버 재시작 시 기존 토큰은 무효가 되며 다시 로그인해야 한다. 여러 worker 간에도 세션이 공유되지 않는다.

## 4. 데모 시나리오

### ALLOW

1. `안전 예시 채우기`를 누른다.
2. `전송 전 검사`를 누른다.
3. 입력 조치 `ALLOW`, 출력 조치 `SKIPPED`, Validator `미실행`을 확인한다.
4. `Proxy 요청 보내기`를 누른다.
5. Mock LLM 응답 이후 출력 조치와 Validator 실제 결과를 확인한다.

### MASK

1. `개인정보 예시 채우기`를 누른다.
2. 사전 검사에서 `MASK`, 상세 전화번호·이메일 탐지, 마스킹 미리보기를 확인한다.
3. `마스킹 적용`을 누른다. 원문 전화번호·이메일이 입력에서 사라지고 이전 결과가 초기화되어야 한다.
4. 다시 검사하거나 프록시로 보낸다. 서버는 수정된 입력을 다시 검사한다.

### WARN

정책 또는 테스트 fixture가 WARN을 반환하면 경고 배너를 확인한다. 같은 입력을 전송할 때 확인 대화상자가 나타나며, 취소하면 요청을 보내지 않는다. 현재 기본 합성 예시에서 WARN이 자연 발생하지 않을 수 있으므로 발표에서 이를 실제 브라우저 검증 완료로 과장하지 않는다.

### BLOCK

1. `프롬프트 인젝션 예시 채우기`를 누른다.
2. 사전 검사에서 `BLOCK`, 인젝션 reason_code, 출력·Validator `SKIPPED`를 확인한다.
3. 전송 버튼이 잠기는지 확인한다.
4. 입력을 바꾸면 이전 BLOCK 결과가 초기화되고 전송 버튼이 다시 열리는지 확인한다.

백엔드는 UI 버튼과 무관하게 모든 `/proxy/chat` 요청의 입력을 다시 검사하며, 차단 입력은 upstream을 호출하지 않는다.

## 5. 관리자 요약

1. 서버에 설정한 `ADMIN_API_TOKEN` 값을 관리자 토큰 필드에 입력한다.
2. `관리자 요약 새로고침`을 누른다.
3. 전체 감사 로그 기반 통계와 최근 BLOCK 이력, reason_code 검색을 확인한다.

잘못된 토큰이면 서버가 401을 반환하고 UI는 토큰과 기존 관리자 데이터를 지운다. 서버 토큰이 미설정이면 503으로 거부한다. 이 토큰 방식은 계정별 RBAC가 아니다.

## 6. 오류 복구

- 401: 사용자 세션을 지우고 로그인 화면으로 이동한다.
- 403: 권한 부족으로 표시한다.
- 422: FastAPI 필드별 validation 메시지를 표시한다.
- 429: 잠시 후 재시도하도록 안내한다.
- 5xx: 서버 처리 실패로 표시하고 이전 관리자 수치를 최신 값처럼 남기지 않는다.
- 네트워크 실패·시간 초과: 세션 만료와 구분한다. 페이지 새로고침 또는 서버 상태 확인 후 재시도한다.
- API 주소 변경: 현재 인증을 지우므로 새 서버에서 다시 로그인한다.

## 7. 검증 명령

```powershell
python -m pytest backend/tests/test_auth_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_admin_api.py backend/tests/test_proxy_e2e.py backend/tests/test_demo_ui_contract.py -q
git diff --check
git status --short --branch
```

실제 외부 LLM 검증은 별도 API 키·비용·승인이 있는 경우에만 수행한다. 기본 완료 기준은 합성 입력과 Mock upstream이다.
