# MVP 멘토링 인쇄 자료

2026-10-14 제작. 팀명 프라이버시가드, 팀원 이름 제외.

## 출력할 파일

- `PrivacyGuard_MVP_A4_Handout.pdf`: A4 세로 3페이지. 고객·시나리오·MVP 우선순위·현재 상태, 완료조건·보안 경계, UI·멘토 질문·메모 공간. 멘토와 함께 검토할 요약본.
- `PrivacyGuard_MVP_Slides_Print.pdf`: A4 가로 7페이지. 제출한 UI 포함 멘토링 PPT 그대로의 인쇄본. 글꼴 대체와 자동 맞춤 차이를 피하도록 2배 해상도 렌더링 이미지를 고정 배치했다. PDF 내 슬라이드 본문은 편집·텍스트 검색용이 아니다.

인쇄 설정: A4, 한 면에 한 페이지, 실제 크기 또는 페이지 맞춤. 요약본 세로, PPT 인쇄본 가로. 멘토용과 본인용 각 1부가 편리하다. 프린터로 실제 출력하거나 인쇄 작업을 전송하지는 않았다.

## 내용의 기준과 한계

기준: `deliverables/mvp_mentoring_ui_2026_10_13/PrivacyGuard_MVP_Mentoring_UI.pptx`, 현행 통합·Validator·PQC·보안 문서와 통합 검증 보고서.

고객 가치·운영 성능은 미검증이며, 평균 50ms·동시 100건은 미검증 목표 후보다. pytest 205 passed, 1 skipped는 2026-10-12 보고서 기록이고 프런트 30 passed는 2026-10-13 기존 실행 결과다. 이번 인쇄본 제작 중 테스트·성능 평가를 새로 수행하지 않았다.

UI는 저장된 실제 로컬 브라우저 화면이며 합성 계정·Mock 응답이다. 새 캡처나 실제 OpenAI 호출 증빙이 아니다. 화면의 TEAM ORCA는 기존 UI 표기다. 채팅은 실제 멀티턴이 아니다.

서명은 ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조다. 실제 ML-DSA·해시 체인·실시간 감시와 구분한다. SSE는 전체 버퍼링 후 출력 검증한다. 감사 로그에는 raw prompt·raw response·API key·system prompt·개인정보 원문을 저장하지 않는 원칙을 유지했다.

## 검증

- PDF 다시 열기: 요약 3페이지, PPT 인쇄본 7페이지 확인.
- 요약 PDF의 주요 한국어 텍스트 추출 확인, 한글 글꼴 포함.
- Poppler로 최종 PDF 전체 10페이지 렌더링·육안 확인. 글자 겹침·잘림 없음.
- `git diff --check`, `git status --short --branch` 실행.
- 초기 fitz 모듈 확인은 실패했으나 설치 없이 번들 Poppler로 정상 렌더링했다.
- 기존 모델 변경과 `.worktrees/`는 수정·커밋하지 않았다.
