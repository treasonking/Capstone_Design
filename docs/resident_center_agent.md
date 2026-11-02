# 주민센터 안내 에이전트 통합

기존 사용자 채팅(`/app`)에서 **주민센터 안내**를 선택해 사용한다. 별도 에이전트 서버나 터미널 앱을 실행하지 않는다.
일반 질문과 관리자 진단의 기존 기본 동작은 유지한다.

## 연결 구조

```text
로그인·기존 사용자 채팅 → /proxy/analyze (분석만, 자료 검색·모델 호출 없음)
                      → /proxy/chat (assistant=resident_center)
                      → 기존 입력 탐지·정책·Provider 직전 마스킹
                      → 업무 키워드로 로컬 공개자료 검색
                      → 기존 OpenAI Provider에 전문 역할·검색자료와 처리된 질문 전달
                      → 답변에 검색 출처 추가 → 기존 Validator → 감사 로그 → 사용자 채팅
```

`/proxy/chat/stream`에서도 같은 검색과 출력 검사를 수행하며 전체 응답을 버퍼링한 후 반환한다.
인증·관리자 토큰·서버 정책·Provider 선택은 기존 규칙을 유지한다.
요청에서 API 키·Provider·시스템 지침을 지정할 수 없다. 미지정 `assistant`는 `general`이며 알 수 없는 값은 422로 거부한다.
검색에는 Provider 직전 처리된 현재 질문과 이력만 사용한다. 검색자료는 고정 JSON이며 사용자 업로드·실시간 수집은 미지원이다.
원문 질문·응답·시스템 지침·검색어를 감사 로그에 추가하지 않는다.

## 대화 연결

같은 안내 유형의 성공한 최근 대화 최대 6쌍을 브라우저 메모리에서 전달한다. 유형이 바뀌면 이전 유형 이력을 섞지 않는다.
실패·차단된 답변은 이력에 넣지 않는다. 재시도는 최초 요청 시점의 질문·유형·이력 스냅샷을 사용한다.
새 대화, 로그아웃, 화면 이탈, 새로고침 시 이력이 초기화된다. 대화 DB는 만들지 않는다.

API `history`는 `user`/`assistant`가 번갈아 나오는 최대 12개 항목이다. 항목별/현재 질문은 4,000자,
총 내용은 20,000자로 제한한다. UI는 이력 16,000자 이내에서 최근 완전한 쌍만 선택한다.
서버는 이력과 질문을 합친 입력 전체에 탐지·정책·egress 마스킹을 다시 적용한다.
과거 답변도 사용자 제공 데이터이며 실제 Provider의 `assistant`나 `system` 역할로 승격하지 않는다.
따라서 `history` 위조로 시스템 권한을 얻을 수는 없지만, 모델이 비신뢰 이력의 내용을 따르는 위험까지 보장하여 제거하지는 않는다.

현재 질문에 업무명이 있으면 새 업무를 검색한다. `대신 가도 돼?`, `수수료는 얼마야?` 같은 후속 표현이면
가장 최근 사용자 발언의 업무를 참고한다. 키워드·후속 표현 기반이므로 일반적인 문맥 이해/업무 전환을 완벽하게 보장하지 않는다.

## 실행

기존 OpenAI 실행 방법 그대로 `OPENAI_API_KEY`, `OPENAI_MODEL`을 로컬 환경변수에 설정한 뒤:

```powershell
./.venv/Scripts/Activate.ps1
./scripts/run_proxy_openai.ps1
```

기존 프런트엔드 실행·회원가입·로그인을 거쳐 `/app`에서 안내 유형을 선택한다.
별도 터미널에서 같은 가상환경을 활성화하고 `python frontend/dev_server.py`로 화면 서버를 실행한다.
기본 `LLM_PROVIDER=mock`은 기존 Mock 응답만 생성한다. 전문 답변 생성·품질 확인은 OpenAI 설정 후 수행해야 한다.
프로젝트는 `.env`를 자동 로드하지 않으므로 키를 파일에 쓰는 것만으로 연결되지 않는다.

시연 질문:

- `전입신고 방문 준비물 알려줘`
- `주민등록등본 직접 발급받으려면 뭘 가져가야 해?`
- `인감증명서 대리 발급 준비물 알려줘`
- `복지 수급 자격이 되는지 알려줘` — 미수록 업무는 확인 불가 안내가 기대된다.

## 자료와 한계

자료는 공식 공개 페이지를 2026-11-02 확인하여 업무별로 수동 요약한 **10건**이다. `backend/app/data/resident_center_services.json`에
출처·지역·확인일·시행일 미확인·추가 확인 질문·한계를 함께 저장한다.

| 업무 | 공식 출처 |
|---|---|
| 전입신고, 등초본, 인감증명, 출생신고, 사망신고, 확정일자 | [구로구 수궁동 우리동 민원](https://www.guro.go.kr/www/contents.do?key=2072) |
| 주민등록증 재발급 | [행정안전부 주민등록증 안내](https://www.mois.go.kr/frt/sub/a06/b06/IDCard_3/screen.do) |
| 가족관계등록 증명서 | [도봉구 증명서 발급신청](https://www.dobong.go.kr/Contents.asp?code=10009933) |
| 본인서명사실확인서 | [행정안전부 정책브리핑](https://www.korea.kr/news/policyNewsView.do?newsId=148927465) |
| 대형폐기물 배출 | [구로구 대형폐기물 안내](https://www.guro.go.kr/www/contents.do?key=2650) |

원문에 오래된 연령 표현이 있어 관련 예외는 제외했다. 요약도 현행 법령과 대조를 완료한 공식 업무 지침은 아니다.
지역이 다르거나 요건이 누락되면 담당기관 확인을 요구하도록 지시한다.
자료 수정 후 원문을 검토하고 서버를 재시작한다. JSON은 패키지와 기존 Docker 빌드에 포함된다.

서버가 검색을 수행하는 기초 RAG 방식이다. 모델 재학습·파인튜닝이나 자율 도구 호출 루프는 도입하지 않았다.
검색은 키워드 매칭으로 표현 차이에 따른 미탐이 있다. 모델 재학습 없이 검색자료와 검사된 이력으로 문맥을 제공한다.
법령 API·행정망·개인별 자격 조회·실제 접수 및 발급은 미구현이다.
출처는 **검색된 참고자료**이며 모델 주장의 자동 사실검증 결과가 아니다. 근거 일치·환각·간접 인젝션 방어를 보장하지 않는다.
Validator는 기존 출력 안전성 검사를 수행하며 행정 안내의 법적 정확성을 검증하지 않는다.
PQC는 기존 ML-DSA 교체 가능한 인터페이스와 Mock signer 기반 구조 그대로다.

구현 근거: [OpenAI Responses API](https://developers.openai.com/api/reference/responses/overview).

## 정상·공격 질문 검증

`evaluation/datasets/resident_center_scenarios.json`의 민원·후속 질문·업무 전환·이력 공격·PII·위험 출력 사례를
`backend/tests/test_resident_center_conversation.py`에서 실제 인증 API 경로로 검증한다.
Provider만 합성 응답으로 대체하고 입력 정책·마스킹·출력 Validator·감사 로그는 실제 코드를 실행한다.

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_resident_center_conversation.py -q --junitxml=reports/resident_center_conversation_results.xml
node --test frontend/demo_async.test.js
```

이 검증은 내부 시나리오 회귀 검사이며 모델의 실제 답변 정확도나 일반적인 공격 방어 성능을 측정하는 벤치마크가 아니다.
