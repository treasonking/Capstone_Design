# Lakera-Balanced Evaluation Report

- Generated at: `2026-05-29T21:26:24`
- Eval path: `evaluation\lakera_balanced_eval.jsonl`
- Lightweight threshold: `0.30`
- Model version: `external-tuned`
- Classifier status: `enabled`
- Runtime: datasets `4.8.5`, sklearn `1.7.2`

## Dataset Construction

| Source | Count | Label |
|---|---:|---|
| Lakera attack samples | 300 | injection |
| Public-sector benign work prompts | 300 | benign |
| Total | 600 | binary |

## Why this dataset was added

The original `Lakera/gandalf_ignore_instructions` subset is attack-only, so FP/TN and balanced Precision/F1 are not meaningful. We keep the original Lakera result as an attack-recall stress test and add `Lakera-balanced` as a separate binary classification evaluation set.

원본 Lakera는 데이터셋 구조상 Precision/F1 산출이 부적절하므로 N/A로 유지하였다. 대신 정상 업무 문장을 추가한 Lakera-balanced 평가셋을 별도로 구성하여 Precision/F1을 산출하였다.

## Results

| Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN | Avg Latency(ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rule Only | 1.0000 | 0.4300 | 0.6014 | 0.7150 | 129 | 0 | 300 | 171 | 0.595 |
| Lightweight Model Only | 1.0000 | 0.9867 | 0.9933 | 0.9933 | 296 | 0 | 300 | 4 | 4.000 |
| Hybrid / Full Pipeline | 1.0000 | 0.9867 | 0.9933 | 0.9933 | 296 | 0 | 300 | 4 | 6.574 |

## Interpretation

`Lakera-balanced` is not a replacement for the original Lakera attack-recall stress test. It is an additional balanced benchmark created to compute FP/TN, Precision, and F1 under a mixed benign/attack setting.

이 결과는 원본 Lakera의 N/A를 0 또는 다른 숫자로 대체한 것이 아니다. 원본 `Lakera/gandalf_ignore_instructions`는 계속 attack-recall stress test로 해석하고, `Lakera-balanced`는 정상 업무 문장이 포함된 별도 binary classification 평가셋으로 해석한다.
