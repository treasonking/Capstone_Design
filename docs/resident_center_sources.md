# 주민센터 공개자료 출처 검토표

검토일: 2026-11-02. 대상: `backend/app/data/resident_center_services.json` 10개 업무.
공개 민원 안내를 수동 요약한 데모용 자료이며 행정기관의 공식 업무 지침을 대체하지 않는다.

## 대조 근거

| 자료 ID | 공식 출처 | 이번 대조 방식 | 보강·확인 범위 |
|---|---|---|---|
| move-in | [정부24 전입신고](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016) | 공식 검색 추출문 | 본인·대리·온라인 구분, 상황별 신분 확인 |
| resident-copy | [정부24 등초본](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000015) | 공식 검색 추출문 | 신청 경로·위임 서류·경로별 수수료와 예외 |
| seal-certificate | [정부24 인감증명](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000025), [행정안전부 온라인 도입 안내](https://www.korea.kr/news/policyNewsView.do?newsId=148934534) | 공식 검색 추출문 | 대리 방문과 온라인 본인 신청 구분, 용도 제한 |
| id-card-reissue | [행정안전부 주민등록증 재발급](https://www.mois.go.kr/frt/sub/a06/b06/IDCard_3/screen.do) | 페이지 본문 해당 구간 | 분실·훼손·사전 정정 절차, IC 비용과 면제 구분 |
| family-certificate | [도봉구 증명서 발급신청](https://www.dobong.go.kr/Contents.asp?code=10009933) | 페이지 본문 해당 구간 | 본인·배우자·직계혈족·대리인, 방문·인터넷 안내 |
| birth-report | [정부24 출생신고](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=12700000045) | 공식 검색 추출문 | 기본 증빙·신분 확인·온라인 신고 기관 |
| death-report | [정부24 사망신고](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=12700000059) | 공식 검색 추출문 | 방문·우편, 증빙·전산확인 시 생략 가능 서류 |
| fixed-date | [구로구 수궁동 우리동 민원](https://www.guro.go.kr/www/contents.do?key=2072) | 페이지 본문 해당 구간 | 계약서 원본 확인과 방문 절차 |
| signature-certificate | [정부24 본인서명사실확인서](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13110000047) | 공식 검색 추출문 | 본인 방문, 한시 면제 종료일, 전자 확인서와 구분 |
| bulky-waste | [구로구 배출 신청안내](https://www.guro.go.kr/www/contents.do?key=2650), [수궁동 우리동 민원](https://www.guro.go.kr/www/contents.do?key=2072) | 페이지 본문 해당 구간 | 지역 한정 신청 경로·주민센터 방문 예외 |

`national` 7건: move-in, resident-copy, seal-certificate, id-card-reissue, birth-report,
death-report, signature-certificate. 나머지 3건은 `local`이며 원문 지자체 범위만 안내한다.
국가 제도에 관한 내용이라도 지역 페이지로만 대조한 문서는 전국 적용을 검증한 자료로 올리지 않는다.

## 접근·해석의 한계

- `official_search_extract`: 공식 도메인 페이지의 검색 추출문을 대조했다. 일부 정부24 URL은 직접 열었을 때 접근 안내와 메뉴만 추출됐다. 이를 전체 원문 확인 성공으로 기록하지 않는다.
- `page_text`: 해당 업무의 본문 구간을 확인했다. 링크 접속 성공이나 문구 존재는 법령의 최신성과 정확성을 증명하지 않는다.
- 전입신고는 정부24 URL별 추출문에 서류 표기가 달라, 임대차계약서를 모든 경우 필수로 일반화하던 지역 요약을 공통 조건으로 사용하지 않았다. 상세 서류는 관할기관 확인으로 남겼다.
- 도봉구 원문의 무인발급기 무료 안내는 지역 수수료 예외일 수 있어 전국 공통 금액으로 수록하지 않았다.
- 구로구 종합 페이지에는 과거 주택임대차신고 계도기간과 구형 표현이 남아 있다. 해당 문구를 현재 요건으로 확장하지 않았으며 이번에는 확정일자와 배출 경로 구간만 사용했다.
- 온라인 인감증명 용도 제한의 보조 자료는 2024년 도입 발표다. 후속 개정 전체 대조는 미완료다.
- 모든 `effective_date`는 `null`이다. 이번 확인일, 원문 게시일·내용 수정일, 법령 시행일을 혼동하지 않는다.
- 공개 페이지 전체를 복제하지 않고 필요한 안내만 요약했다. 사용자 민원 내용·실제 개인정보·신청서 작성 내용은 자료에 넣지 않는다.

## 특정 센터 적용 전 확인

‘행복 주민센터’의 실제 시·군·구와 동은 미확정이다. 현재 자료에는 운영시간·휴무·대표전화·담당 창구·
무인발급기 위치를 등록하지 않았다. 이름이 비슷한 센터를 임의로 선택하거나 일반적인 업무시간을 대입하지 않는다.

센터가 정해지면 해당 지자체 공식 센터 페이지로 명칭·주소·연락처·업무별 담당을 확인하고,
센터 운영정보와 전국 공통 제도 자료를 구분해 등록한다. 공휴일·임시 휴무·야간창구·특정 업무 가능 여부는 별도 대조한다.

## 갱신 절차

1. 공식 원문과 필요한 예외·기간·지역을 확인한다. 일부만 읽혔으면 접근 한계를 기록한다.
2. 자료 ID를 유지하고 본문·범위·출처·`source_access`·확인일·한계를 함께 수정한다.
3. 한시 면제·요금·접수 경로를 다시 대조한다. 증빙이 없으면 미확인으로 남긴다.
4. 주민센터 통합 테스트와 보안 회귀를 실행하고 새 결과를 별도 보고서로 기록한다.
5. JSON 로드 캐시 반영을 위해 서버를 재시작한다. 현재 자동 수집·주기적 갱신 기능은 없다.

이번 코드 검증: [자료 보강 검증 보고서](../reports/resident_center_sources_verification.md).
