# 사용자 채팅·관리자 재통합 검증

## 환경·기준 커밋

- 실행일: 2026-10-12 KST, Windows PowerShell, Python 3.12.14, Node.js.
- 대상 브랜치: `wkdnjs5665-login-signup-ui`.
- UI 기준: `bce22d6f562b38d1453c2a29d52125eb3082e653`.
- 통합 master: `a89edc7280919d12242352631e2218b8668b1761`. 최종 커밋 직전 fetch에서도 동일했다.
- 구현·검증은 `.worktrees/user-chat-admin`에서 수행했다. 이 보고서를 포함하는 통합 커밋은 `git log -1 --format=%H -- reports/user_chat_admin_integration_verification.md`로 식별할 수 있다.
- 원래 checkout의 수정된 `models/lightweight/classifier.joblib`를 복사·학습·덮어쓰기하지 않았다. 보존 확인 SHA256: `02F814970B8596C07DB774EE185EC25DD777734E462F8EFE9CB399321A1AA67E`.
- UI 기본 포트 **5500**, API 기본 **8000** 유지. 브라우저 검증 전용 UI **5520** / API **8020** / Mock upstream **8021**. 사용자 5500·8000 서버는 중지·교체하지 않았다.
- Browser는 Codex In-app Browser의 실제 페이지다. API와 `tools.mock_llm` 서버는 로컬 네트워크로 실제 통신했다. 브라우저 검증의 탐지는 `ENABLE_MODEL_DETECTOR=false`이며 정확도 평가가 아니다.
- 테스트 계정은 임시 SQLite DB의 합성 계정이며 외부 OpenAI 키나 실제 개인정보를 사용하지 않았다. 별도 worktree 감사 로그에는 합성 테스트의 기존 감사 메타데이터만 생성됐다.

## 실행 결과

| 실제 명령/검증 | 결과 |
|---|---|
| `node --test frontend/demo_async.test.js` | 30 passed, 0 failed, 0 skipped. 기존 timeout·인증·관리자 15건 의미 유지 + 채팅/보안 회귀 |
| focused pytest: auth, admin, proxy, analyze, Provider 통합, UI 계약 | 최초 49 passed |
| `python -m pytest -q -p no:cacheprovider backend/tests/test_user_chat_contract.py backend/tests/test_ui_routes.py` | 16 passed |
| `RUN_LIVE_OPENAI_TESTS=0`, `python -m pytest -q -p no:cacheprovider` | 205 passed, 1 skipped. live OpenAI 테스트 의도적 skip |
| JS 구문 `node --check -` | pytest UI 계약 검사에서 통과 |
| UI fallback의 `/`, `/demo.html`, 네 화면, query/trailing slash | 다른 cwd에서 실제 임시 HTTP 서버 요청으로 18 조합 통과 |
| `/missing.js`, `/auth/signup`, `/proxy/chat`, `/unknown` 정적 서버 요청 | 404 확인. API를 HTML 200으로 숨기지 않음 |
| `git diff --check` | 통과 |

pytest 경고는 기존 FastAPI `on_event` deprecated 및 NumPy/joblib 직렬화 경고다. 탐지기·데이터셋·평가 로직·성능 수치를 변경하지 않아 외부 데이터셋 평가를 이번 로컬 UI 작업에서 재실행하지 않았다. CI의 기존 내부/외부 샘플 평가 job은 유지했다.

## 시나리오별 증거와 미검증 구분

| ID | 실제 확인 결과 |
|---|---|
| AUTH-01 | 브라우저 합성 가입 → `/login` 성공 안내/이메일 유지 → 로그인 → `/app` → 새로고침 세션 복원 → 로그아웃/화면 정리 확인. API 테스트도 통과 |
| AUTH-02 | Node VM에서 timeout 토큰 유지·401 제거·후속 복원 성공. 브라우저에서 일시 연결 실패 후 토큰 유지 안내와 새로고침 복원도 확인 |
| CHAT-01 | 실제 브라우저에서 공개 질문과 최종 Mock 답변 누적 확인 |
| CHAT-02 | 실제 브라우저에서 합성 전화/이메일 마스킹 안내 확인. API 테스트에서 원문이 Provider에 전달되지 않음 확인 |
| CHAT-03 | 브라우저 입력 인젝션 차단 안내/답변 미표시. 출력 차단은 API+Node로 검증 |
| CHAT-04 | Node VM에서 WARN 취소 시 chat 호출 없음, 확인 시 원래 snapshot 전송. 브라우저에서는 계좌번호 WARN 요청의 마스킹된 최종 응답을 확인했으나 확인/취소 대화상자 선택 자체는 자동화 도구에서 관찰하지 못함 |
| CHAT-05 | 빈 입력·IME 조합·연속 제출은 Node. Enter 및 Shift+Enter 줄바꿈은 실제 브라우저 확인 |
| CHAT-06 | 실제 검증용 Mock PID를 중지해 Provider 오류, 입력/버튼 복구, 수동 재시도 표시 확인. Mock 복구 후 실패한 원래 질문으로 재시도 성공. 15초 경계 timeout은 Node 검증 |
| CHAT-07 | 헤더와 body 지연 timeout은 Node VM 검증. 실제 브라우저 지연 body 주입은 미실행 |
| CHAT-08 | Node에서 전송 중 새 대화/화면 이동/로그아웃/pagehide 및 늦은 응답·finally·401 무효화. 실제 브라우저 화면 이동·새 대화·로그아웃 기록 정리 확인 |
| CHAT-09 | HTML 모양 입력/답변의 literal textContent는 Node, innerHTML 미사용은 정적 검사. 실제 브라우저 XSS 공격 시나리오는 미실행 |
| ADM-01 | 실제 브라우저 토큰 누락/오류 거부, 유효 토큰 집계·설정·진단 표시. 일반 Bearer만으로 접근 불가 및 debug 우회 불가는 API 테스트 |
| ADM-02/03 | Node에서 토큰/origin/세션 변경·로그아웃 중 늦은 조회 차단, timeout stale 수치 정리·토큰 유지·재조회 성공 |
| ROUTE-01 | 네 경로·query·trailing slash는 HTTP 자동 테스트. 브라우저 `/signup`, `/login`, `/app`, `/admin` 진입·전환·새로고침 확인 |
| VIEW-01 | 실제 1024×768 데스크톱, 390×844 모바일 확인. 긴 Provider JSON 가로 넘침을 발견해 overflow-wrap 수정 후 page width 375 ≤ viewport 390 확인. 모바일 OS 소프트 키보드/실제 IME 기기 검증은 미실행 |
| PRIV-01 | 원문/최종 응답 감사 로그 미기록 API 회귀, 일반 사용자 projection의 내부 필드 제거, 대화·관리자 토큰 저장소 미사용 코드 검사/Node 확인. 실제 사용자 데이터는 사용하지 않음 |

Node VM/Fake DOM 결과는 실제 브라우저 결과가 아니다. 실제 OpenAI 호출은 **미실행**, live test **skip**이다. 실제 ML-DSA나 외부 데이터셋 성능 향상은 검증하지 않았다.

## 발견·수정 및 운영 한계

- 병합 충돌: `frontend/demo.html`의 경로 전환과 master 비동기 상태 제어를 기능별 병합했다.
- 모바일 관리자 Provider 설정의 긴 문자열 overflow를 실제 브라우저에서 발견·수정했다.
- 이전 프록시 요청의 401이 새 세션을 지울 수 있는 경로에 요청 token/origin 소유권 검사를 추가하고 회귀를 통과했다.
- 테스트 중 Windows asyncio transport에 일시적인 `WinError 10054`가 기록됐다. 원시 오류는 사용자 채팅에 노출되지 않았고 API의 후속 HTTP 200, 브라우저 세션 복원 및 재시도 성공을 확인했다. Windows 연결 중단 시 transport 경고 자체를 제거하는 변경은 하지 않았다.
- Python 기본 명령이 PATH에 없어 기존 저장소 `.venv/Scripts/python.exe`로 실행했다. `.git` 쓰기는 sandbox에서 거부되어 승인된 Git 작업으로 수행했다. 프로세스 목록 CIM 조회도 기본 권한에서 거부되어 직접 시작 PID와 테스트 로그의 PID만 사용했다.
- 화면 기록은 단일 질문/답변이며 실제 멀티턴이 아니다. 관리자 토큰은 RBAC가 아니고, 감사 서명은 ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조다.
- 기존 상세 API 소비자는 관리자 인증 헤더가 추가로 필요하다. WARN 확인은 UI 절차이며 서버의 BLOCK을 해제하지 않는다. 수동 재시도에도 서버 중복 처리 가능성은 남는다.

## 스크린샷

합성 계정과 공개 테스트 질문만 사용했다. 비밀번호·토큰 원문·실제 대화는 포함하지 않았다. 캡처는 데모 증거이며 탐지 정확도/성능 측정이 아니다.

- [사용자 데스크톱](assets/user-chat-desktop.jpg)
- [사용자 모바일](assets/user-chat-mobile.jpg)
- [관리자 현재 요청 상세](assets/admin-diagnostic-desktop.jpg)

## GitHub 반영

대상 UI 브랜치에 일반 커밋·푸시하고 master 대상 PR로 리뷰한다. master 직접 푸시·force push·자동 병합은 하지 않는다. 로컬 통과와 CI 통과는 별개이며 실제 PR/CI 결과는 최종 전달 메시지와 PR 검사에 기록한다.
