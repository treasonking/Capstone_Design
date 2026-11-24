# 보안 탐지 학습 데이터 설계

## 목적과 초기 후보

한국어·영어 입력에서 개인정보와 프롬프트 인젝션을 독립적으로 분류한다. 자체 작성한 합성 텍스트를 기본 출처로 삼는다. 민원 맥락은 탐지의 배경으로 쓰며 주민센터 RAG 자료 자체를 학습에서 제외한다. 실제 주민 정보, 실사용 연락처·식별자, 상담 로그의 원문은 수집하지 않는다. 예약 도메인·예시 전화 범위 또는 명시적으로 불가능한 번호를 사용하고, 사람·주소는 허구임을 확인한다.

| 후보 코호트 | 목표 건수 | 생성과 검수 기준 |
|---|---:|---|
| 한국어 PII | 1,000 | 전화, 주민등록번호 형식, 이메일, 주소, 계좌, 문맥상 개인정보, 개인과 연결된 복지·건강 민감정보 |
| 영어 PII | 500 | 같은 의미 범주를 언어에 맞는 표현과 입력 맥락으로 독립 작성 |
| 한국어 Injection | 1,000 | 지시 우선순위 변경, 시스템 지침 요구, 정책 무력화, 문서 내 간접 지시 |
| 영어 Injection | 1,000 | 같은 위협 범주, 독립 작성 및 정상 인용과의 쌍 검수 |
| 정상 주민센터 업무 | 1,500 | 민원·복지·서류 발급 문의 및 정상 요약 |
| Hard Negative | 1,000 | 보안 교육·분석·인용, 개인정보 형식과 비슷한 물품번호·일반 식별자, 값 없는 필드 언급 |
| 난독화 | 1,000 | 가상 이메일의 표기 변화 등 표현 변형의 양성·음성 쌍. 원본과 같은 그룹 |

7,000건은 목표다. 중복 합산을 막기 위해 각 샘플의 집계 코호트는 하나만 두되 두 탐지 플래그는 동시에 참일 수 있다. 템플릿마다 의도·문맥·업무 상황을 다양화하고, 두 검수자가 독립 판정한 뒤 불일치를 조정한다. 의미 변화 없는 복제는 제거하고 애매하거나 실제 데이터로 보이는 행은 보류한다.

## 출처와 권리

| 출처 | Phase 2 처리 |
|---|---|
| 자체 작성 합성 데이터 | 우선 사용. 작성 방식, 템플릿 계열, 검수 결과와 승인자를 manifest에 기록한다. |
| deepset / Lakera | 공개 카드에 각각 Apache-2.0 / MIT 표시. 기존 진단과 파생 계열을 지킬 수 있도록 초기 학습 후보에서 두 출처 전체를 제외한다. [deepset 카드](https://huggingface.co/datasets/deepset/prompt-injections) · [Lakera 카드](https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions) |
| ProtectAI | 원본 카드 접근 확인에서 HTTP 401. 미러의 파일과 권리 출처를 확인할 때까지 학습에서 제외한다. 기존 부분집합은 저장소 진단용으로 유지한다. [원본 카드](https://huggingface.co/datasets/protectai/prompt-injection-validation) |
| AI4Privacy OpenPII 1M | 카드에 CC BY 4.0과 합성 데이터로 표시된 영어 PII 후보. 표시·변경 내역을 남기고, 이용하려는 revision에서 영문 어휘·레이블·유사 중복과 실제 식별자 혼입 여부를 검수한다. 한국어 행정 맥락은 자체 합성한다. [데이터 카드](https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m) |
| AI4Privacy pii-masking-400k | 합성 PII 후보 조사용. 공개 라이선스에 연구 승인, 배포·파생물에 별도 권리 조건이 있어 허가가 확정되기 전 학습 및 재배포에서 제외한다. [라이선스](https://huggingface.co/datasets/ai4privacy/pii-masking-400k/blob/main/LICENSE) |

공개 후보 채택 시 원본 URL·revision·라이선스 사본과 파생 모델·데이터 공개 가능 범위, 원문 출처, 레이블 매핑, 개인정보 검수를 manifest에 남긴다. Phase 1 샘플은 자체 합성이다.

## 레코드와 학습 변환

[9개 소규모 JSONL 샘플](security_dataset_samples.jsonl)은 검수 및 형식 확인용이다. 학습·검증·최종 Holdout에 편입하기 전에 분할 규칙을 적용하며 이번 단계에는 편입하지 않는다.

- 입력은 `text`다. `id`, `language`(ko/en/mixed), `domain`, `source`, `group_id`, 코호트·근거·검수·라이선스는 메타데이터다. 후속 manifest에서 원본 ID와 파생 계열 ID도 관리한다.
- 정답은 두 boolean, 복수 `pii_types`, nullable `injection_type`, 파생 `reason_code`다. 빈 PII 배열은 PII 음성, null 인젝션 유형은 인젝션 음성이다. `reason_code`는 플래그 조합에 따라 NORMAL / PII_PRESENT / INJECTION_PRESENT / BOTH_PRESENT로 고정한다. 운영 `ReasonCode`는 정책과 검출기가 결정한다.
- PII 세부 태그는 PHONE, EMAIL, GOVERNMENT_ID, ACCOUNT, ADDRESS, CONTEXTUAL, SENSITIVE_HEALTH, SENSITIVE_WELFARE, OBFUSCATED다. 로컬 출력은 단일 유형이다. 우선순위는 OBFUSCATED → GOVERNMENT_ID → ACCOUNT(FINANCIAL) → ADDRESS → PHONE/EMAIL(CONTACT) → 문맥·민감정보(OTHER)다. PII 음성은 CLEAR다. 검수 메타데이터에는 전체 유형을 유지한다.
- 인젝션은 PROMPT_INJECTION / SYSTEM_PROMPT_REQUEST / POLICY_BYPASS로 투영한다. 간접성, 언어, 난독화는 메타데이터에 남긴다. 복합 의도는 시스템 지침 요구 → 정책 우회 → 일반 인젝션 순으로 대표 유형을 부여한다. 음성은 CLEAR다.
- SFT는 기존 [Ollama 입력 형식과 LocalVerdict](../../backend/app/detection/ollama_detector.py)를 따른다. system에는 고정 분류 지침을, user에는 `normalize_for_ollama(text)`를 적용한 `{"text":"..."}`를, assistant에는 예를 들어 `{"pii":"CONTACT","injection":"SYSTEM_PROMPT_REQUEST"}`를 넣는다. 두 필드는 독립이다. confidence와 정책 조치는 SFT 타깃에서 제외한다. 정규화로 판정 근거가 바뀌는 행은 원문과 정규화본을 함께 검수한다.

## 평가 오염 방지

1. 기존 내부 평가와 관련 파생본(`datasets/sample_dataset*.json`, `evaluation/sample_dataset.json`, `evaluation/datasets/`, `evaluation/external_validation_sample.json`), 공개 평가 부분집합(`reports/baselines/multi_dataset/*_shared_eval.csv`, 기존 평가용 원본·스플릿), `evaluation/adaptive_compare.py`의 합성 송신 케이스를 제외 manifest로 고정한다. 이전 외부 튜닝의 train/eval 로컬 JSONL은 Git에서 무시되므로 준비된 원본·manifest를 다시 확보한다. 자료가 없으면 해당 출처의 재사용을 보류한다.
2. 원문 SHA-256 및 NFKC·format 문자 제거·casefold·공백 정규화 후 SHA-256으로 중복을 검사한다. 형태만 치환한 변형은 값 마스킹 기반 fingerprint, 문자 n-gram 유사도, 양언어 수동 검토를 함께 쓴다. 비교 기준과 검토 결과를 고정하고 평가 텍스트를 SFT 입력에 복사하지 않는다.
3. 같은 원본·템플릿·번역·난독화·유사 행은 연결된 하나의 그룹으로 묶는다. 출처별 미사용 그룹을 확보하고 group 단위 80:10:10을 초기 후보로 언어·레이블·난이도 균형을 확인한다. 분할 간 그룹 ID, 원본 ID, 정규화 해시 교집합과 유사 쌍 검토를 통과해야 한다. 소수 그룹으로 목표 비율이 불가능하면 실제 비율을 기록한다.
4. deepset/ProtectAI/Lakera 등 반복 조회 벤치마크는 진단용이다. 독립 Holdout은 작성자·원천·업무 시나리오·템플릿 계열을 별도 확보한 뒤 학습과 모델 선정 담당자가 볼 수 없게 봉인한다. 버전과 해시를 저장하고 사전 등록한 비교를 확정한 후 한 번 연다. 테스트 세트의 결과를 보고 튜닝하면 해당 세트는 진단용으로 재분류한다.

Phase 1의 9개 샘플은 필드·레이블 일관성과 실제 `LocalVerdict` 변환을 통과했다. 조회 가능한 내부·외부 부분집합 및 합성 사례의 정규화 고유 텍스트 1,083개와 완전·정규화 중복이 없었고, 문자 3-gram Jaccard 최대값은 0.252였다. 이번 표본 검사의 검토 기준은 0.65이며, 다국어 의미 유사도나 저장소에 없는 원본을 확인한 결과로 일반화할 수 없다.
