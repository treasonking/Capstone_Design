# N/A Metric Interpretation

## Purpose

본 문서는 외부 데이터셋 평가표에서 `N/A`로 표시되는 항목의 원인을 설명한다. `N/A`는 성능 0이 아니라, 지표 산출 조건이 맞지 않거나 평가 범위에 포함되지 않는 경우를 의미한다.

## N/A 유형

| Type | Cause | Affected Metrics | Example | Interpretation |
|---|---|---|---|---|
| Positive-only dataset | 정상 샘플이 없어 FP/TN 계산이 불가능 | Precision, F1, FP, TN | Lakera/gandalf_ignore_instructions | Recall stress test로 해석 |
| Model unavailable | model artifact 누락 또는 로딩 실패 | Model Only metrics | artifact_missing | 모델 성능이 아니라 실행 조건 문제 |
| Metric not computed | score 기반 지표 미산출 | AUROC | local proxy baseline | 미측정 |
| Dataset unavailable | 데이터셋 로딩 실패 또는 샘플 없음 | 전체 지표 | unavailable/empty | 평가 불가 |
| Scope mismatch | 데이터셋 목적과 평가 항목 불일치 | PII metrics on prompt-injection datasets | deepset/protectai/Lakera | 평가 범위 밖 |

## Lakera Case

`Lakera/gandalf_ignore_instructions`는 공격 샘플 중심 데이터셋으로 사용하였다. 따라서 정상 샘플을 기반으로 하는 FP/TN이 정의되지 않거나 의미가 약하다. 본 연구에서는 이 데이터셋을 balanced binary classification benchmark가 아니라 ignore-instruction 공격에 대한 recall stress test로 해석한다.

## Lakera-balanced 추가 평가

원본 `Lakera/gandalf_ignore_instructions`는 공격 샘플 중심 데이터셋이므로 Precision/F1을 N/A로 유지한다. 이는 평가 실패가 아니라 지표 산출 조건이 맞지 않기 때문이다.

다만 N/A를 보완하기 위해 정상 업무 문장을 결합한 `Lakera-balanced` 평가셋을 별도로 구성한다. `Lakera-balanced`는 정상 샘플과 공격 샘플을 모두 포함하므로 FP/TN을 정의할 수 있고, Precision/F1을 산출할 수 있다.

따라서 보고서에서는 다음처럼 해석한다.

| Dataset | Interpretation |
|---|---|
| Original Lakera | Attack-only recall stress test |
| Lakera-balanced | Balanced binary classification with benign public-sector work prompts |

## Reporting Rule

논문과 README에서는 다음 표현을 사용한다.

- 잘못된 표현: `Lakera에서 Precision이 0이다.`
- 올바른 표현: `Lakera는 공격 샘플 중심 데이터셋이므로 Precision/F1은 N/A로 표시하고 Recall 중심으로 해석한다.`
- 잘못된 표현: `N/A는 실패다.`
- 올바른 표현: `N/A는 지표 산출 조건이 맞지 않거나 평가 범위에 포함되지 않는다는 의미다.`
