# 팀원 PPT 멘토링 문구 수정본

원본: `C:/Users/jho87/Documents/카카오톡 받은 파일/캡디 MVP 범위 및 요구사항.pptx`

최종: `PrivacyGuard_MVP_Mentoring_Final.pptx` (6장)

사용자 요청에 따라 디자인·글꼴·크기·도형·이미지·배치·장수를 유지하고, 3~6장의 설명 문구만 수정했다. 원본 파일은 수정하지 않았다.

- SSE: 전체 응답 버퍼링 후 Validator 검사와 반환, 실시간 토큰 검증과 구분.
- 탐지·마스킹: PII 패턴 탐지와 인젝션 규칙·경량 분류 구분, 탐지 누락 위험 보존.
- 감사: 레코드별 해시·Mock signer 검증으로 정정, 실제 PQC·해시 체인·실시간 감시 주장 제거. 원문 대신 판정 메타데이터를 저장하는 원칙 유지.
- Should: 구현된 관리자 조회·WARN 확인과 미구현 조직별 정책 편집 구분.
- 50ms·동시 100건: 성능 결과 대신 미검증 목표 후보로 명시. 멘토와 조건·타당성 확인 필요.
- 완료조건: 분리된 코드 표시는 유지하고 주변 문장의 누락을 보완. 기존 마지막 영역에 MVP 범위·성능 목표·다음 개발 우선순위에 관한 멘토 질문 추가.

근거: `docs/validator_agent.md`, `docs/pqc_audit_integrity.md`, `docs/codex_user_chat_admin_integration.md`, `backend/app/integrity/audit_signer.py`, `backend/app/integrity/pqc_signer.py`와 직전 현황 검토.

## 검증

- ZIP 패키지를 비교해 slide3~6.xml의 텍스트 노드 외에는 바이트 단위로 같은 내용을 유지하는지 검사했다. 21개 텍스트 상자 수정, 나머지 패키지 구성요소 65개 동일.
- PPTX 패키지·레이아웃·6장 수·Artifact Tool 재가져오기 검사 통과.
- 원본과 수정본 6장 렌더링 대조. PowerPoint 앱에서 직접 확인하지는 않았다.
- `git diff --check`, `git status --short --branch` 실행.
- 문구 수정만 수행해 탐지 성능 평가와 코드 테스트는 재실행하지 않았다. 기존 모델 변경과 `.worktrees/`는 커밋에서 제외.
