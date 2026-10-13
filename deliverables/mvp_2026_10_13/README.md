# 프라이버시가드 MVP 개정본

- 최종 제출 파일: `PrivacyGuard_MVP_Updated.pptx` (12장)
- 팀명: 프라이버시가드. 팀원 이름 제외.
- 기준: GitHub master `7c5819d81def90b0d1a46297ad66b87ed0ff75cc`, 2026-10-13 확인.
- 이전 10월 12일 PPT는 이력으로 보존한다. 이번 제출에는 이 폴더의 개정본을 사용한다.
- 제출 마감: 2026-10-13 23:00 (Asia/Seoul), 연장 불가. LMS 제출·멘토 전달은 수행하지 않았다.

## 반영 내용

기존 PPTX를 가져와 디자인·텍스트·편집 가능한 표와 12장 구성을 유지하며 수정했다.

- 1장: 개정 날짜 반영.
- 2장: 로그인, 자동 사전 분석, WARN 확인, 안전한 최종 답변 표시, 관리자 근거 확인 흐름.
- 4~5장: 일반 사용자 최소 응답과 관리자 상세 진단의 권한 경계. 사전 분석의 Validator SKIPPED는 상세 응답에서 확인한다. WARN 확인은 서버 정책 차단을 해제하지 않는다.
- 6장: 가입·로그인·사용자 채팅·관리자 UI 구현을 반영. 실제 OpenAI 호출은 미검증으로 명시. 채팅은 메모리 내 단일 질문·답변 기록이며 멀티턴 미구현.
- 7장: `reports/assets/user-chat-desktop.jpg`, `reports/assets/admin-diagnostic-desktop.jpg`의 기존 실제 브라우저 증빙을 사용. 합성 계정·Mock 응답이며 새 캡처가 아니다. UI의 TEAM ORCA는 원본 화면 브랜딩이고 제출 팀명은 프라이버시가드다. 관리자 화면은 현재 요청 상세이며 과거 개별 로그 서명 검증 화면이 아니다.
- 8장: 기존 pytest 통합 205 passed, 1 skipped와 이번 Node 회귀 30 passed를 구분. 과거 focused 17 passed는 전체 결과에 더하지 않는다.
- 11장: 실제 멀티턴·공유 세션·중복 요청 방지 미구현을 명시.

## 사실·평가 경계

근거 문서는 `docs/codex_user_chat_admin_integration.md`, `reports/user_chat_admin_integration_verification.md`, README 및 기존 보안·Validator·PQC 문서다. 실제 OpenAI 호출, 실제 ML-DSA, 운영 부하 및 고객 가치 검증은 완료로 주장하지 않는다.

Validator는 LLM/Mock 출력 생성 후 반환 전의 규칙 기반 검증 계층이다. SSE는 전체 응답 버퍼링 후 검증한다. 서명은 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**다. 감사 로그는 raw prompt, raw response, API key, system prompt, 개인정보 원문을 저장하지 않는 원칙을 유지한다.

9~10장의 수치는 기존 평가 보고서 인용이다. 내부 회귀 113건과 외부 deepset 662건을 분리하고 external-tuned 결과와 혼합하지 않았다. ProtectAI F1의 README 0.3227 / 보고서 0.2950 불일치는 이전 점검에서 사용자에게 경고했고 이번에도 PPT 수치에서 제외했다. 탐지기·데이터셋·평가 스크립트·기존 성능표는 변경하지 않았고 성능 평가를 재실행하지 않았다.

## 이번 검증과 한계

```powershell
node --test frontend/demo_async.test.js
git diff --check
git status --short --branch
```

- 2026-10-13 번들 Node로 직접 재실행: **30 passed, 0 failed**. Node VM/Fake DOM 검사이며 실제 브라우저 재검증과 구분한다.
- 기존 통합 보고서의 2026-10-12 pytest: **205 passed, 1 skipped**. 실제 OpenAI live 테스트는 skip. FastAPI·NumPy/joblib 경고가 기록돼 있다.
- 직전 현황 점검에서 `.venv/Scripts/python.exe -m pytest ...`는 가상환경의 원래 Python 3.12 경로가 없어 시작하지 못했다. 번들 Python에도 pytest가 없어 오늘 Python 테스트를 재실행하지 못했다. 기존 환경은 변경하지 않았다.
- PPTX 패키지·레이아웃·글꼴·편집 가능한 표·재가져오기 검사가 통과했다. 12장 전체를 렌더링해 육안 확인했다. PowerPoint 앱에서 직접 확인하지는 않았다.
- 기존 로컬 classifier 수정과 `.worktrees/`는 보존하고 이번 커밋에서 제외한다.
