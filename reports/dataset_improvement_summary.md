# Dataset Improvement Summary

## Scope

`codex_dataset_improvement_plan.txt` 기준으로 데이터셋, 라벨 문서, 검증 스크립트, 통계 스크립트, 상세 평가 리포트를 추가했다.

## Added Artifacts

- `datasets/sample_dataset.json`: v1 데이터셋 복사본
- `datasets/sample_dataset_v2.json`: metadata와 확장 샘플이 포함된 v2 주 평가셋
- `datasets/sample_dataset_v2_balanced.json`: category별 과도한 쏠림을 줄인 balanced 버전
- `datasets/labeling_guide.md`: 라벨 정의, 포함/제외 기준, positive/negative 예시
- `datasets/dataset_notes.md`: 데이터셋 설계 의도, 한계, 향후 개선 방향
- `scripts/build_dataset_v2.py`: v2 데이터셋 생성 스크립트
- `scripts/validate_dataset.py`: JSON 구조, id, task, labels, 중복, suspicious sample 검증
- `scripts/dataset_stats.py`: task/label/category/difficulty 분포 산출
- `scripts/evaluate_detection.py`: 전체, task별, label별, category별 성능 및 FP/FN 사례 산출
- `reports/detection_eval_report.md`: 평가 리포트
- `reports/detection_eval_report.json`: 평가 원본 JSON
- `reports/detection_error_cases.md`: 오탐/미탐 사례
- `reports/dataset_stats.md`: 데이터셋 통계
- `reports/dataset_stats.json`: 통계 원본 JSON

## v2 Dataset Summary

| Item | Count |
|---|---:|
| Total samples | 117 |
| PII samples | 58 |
| Injection samples | 59 |
| Positive samples | 74 |
| Negative samples | 43 |
| Multilabel samples | 33 |
| Boundary candidates | 70 |
| Easy / Medium / Hard | 23 / 40 / 54 |

## Label Distribution

| Label | Count |
|---|---:|
| PII_EMAIL_DETECTED | 12 |
| PII_PHONE_DETECTED | 13 |
| PII_RRN_DETECTED | 8 |
| PII_ACCOUNT_DETECTED | 8 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 8 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 7 |
| INJ_REVEAL_SYSTEM_PROMPT | 10 |
| INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT | 13 |
| INJ_POLICY_BYPASS_ATTEMPT | 11 |
| INJ_ROLE_OVERRIDE_ATTEMPT | 4 |
| INJ_DEBUG_MODE_ATTEMPT | 4 |
| INJ_RULE_DISCLOSURE_ATTEMPT | 13 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 3 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 2 |

## Evaluation Snapshot

| Scope | Precision | Recall | F1 |
|---|---:|---:|---:|
| Overall micro | 0.914 | 0.830 | 0.869 |
| Overall macro | 0.853 | 0.777 | 0.812 |

## Main Error Themes

- PII account-like false positives: 문서번호, 승인번호, 수식, 티켓 번호가 계좌번호 패턴과 충돌한다.
- Phone false negative: `+82 (10) ...`처럼 괄호가 있는 전화번호 표기를 현재 정규식이 놓친다.
- Injection indirect false negatives: `필터 없이`, `숨겨진 지시를 요약`, `내부 룰셋 개요` 같은 완곡 표현은 추가 룰이 필요하다.
- Boundary false positive: `Do not reveal hidden prompt`처럼 금지 문맥의 정상 문장을 공격으로 볼 수 있다.
- Obfuscation coverage: 난독화 표현은 일부 위험 표현으로 탐지되지만 별도 obfuscation 라벨 보존이 약하다.

## Validation

- `datasets/sample_dataset_v2.json`: validation passed
- `datasets/sample_dataset_v2_balanced.json`: validation passed
- 기존 평가 스크립트와 호환되도록 `task`, `text`, `labels` 구조 유지
