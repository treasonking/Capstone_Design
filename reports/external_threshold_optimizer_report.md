# External Threshold Optimizer

- Generated at: `2026-05-18T22:06:20`
- Evaluation source: `datasets\external_splits\eval_external_prompt_injection.jsonl`
- Threshold candidates: `0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70`
- Model version: `external-tuned`
- Model status: `enabled`

## Recommended Thresholds

| Dataset | Model Version | Mode | Recommended Threshold | Precision | Recall | F1 | FP Rate | Reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| `deepset/prompt-injections` | external-tuned | Lightweight Model Only | 0.30 | 1.0000 | 0.6076 | 0.7559 | 0.0000 | best F1 with precision >= 0.70 preference |
| `deepset/prompt-injections` | external-tuned | Hybrid / Full Pipeline | 0.30 | 1.0000 | 0.6329 | 0.7752 | 0.0000 | best F1 with precision >= 0.70 preference |
| `protectai/prompt-injection-validation` | external-tuned | Lightweight Model Only | 0.30 | 0.9946 | 0.8876 | 0.9381 | 0.0036 | best F1 with precision >= 0.70 preference |
| `protectai/prompt-injection-validation` | external-tuned | Hybrid / Full Pipeline | 0.30 | 0.9488 | 0.8876 | 0.9172 | 0.0363 | best F1 with precision >= 0.70 preference |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Lightweight Model Only | 0.30 | N/A | 0.9867 | N/A | N/A | positive-only dataset; recall-oriented recommendation |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Hybrid / Full Pipeline | 0.30 | N/A | 0.9867 | N/A | N/A | positive-only dataset; recall-oriented recommendation |

## Data Leakage Control

- External datasets were split with random seed `42`.
- Train/eval id overlap: `0`.
- Train size: `3421`, eval size: `1468`.

## Results

| Dataset | Model Version | Threshold | Mode | Precision | Recall | F1 | FP Rate | Recommended |
|---|---|---:|---|---:|---:|---:|---:|---|
| `deepset/prompt-injections` | external-tuned | 0.30 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.0000 | yes |
| `deepset/prompt-injections` | external-tuned | 0.30 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.0000 | yes |
| `protectai/prompt-injection-validation` | external-tuned | 0.30 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.0036 | yes |
| `protectai/prompt-injection-validation` | external-tuned | 0.30 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.0363 | yes |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.30 | Lightweight Model Only | N/A | 0.9867 | N/A | N/A | yes |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.30 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | N/A | yes |
| `deepset/prompt-injections` | external-tuned | 0.35 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.35 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.35 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.0036 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.35 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.0363 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.35 | Lightweight Model Only | N/A | 0.9867 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.35 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.40 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.40 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.40 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.0036 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.40 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.0363 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.40 | Lightweight Model Only | N/A | 0.9867 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.40 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.45 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.45 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.45 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.0036 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.45 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.0363 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.45 | Lightweight Model Only | N/A | 0.9867 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.45 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.50 | Lightweight Model Only | 1.0000 | 0.5570 | 0.7154 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.50 | Hybrid / Full Pipeline | 1.0000 | 0.5823 | 0.7360 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.50 | Lightweight Model Only | 0.9945 | 0.8660 | 0.9258 | 0.0036 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.50 | Hybrid / Full Pipeline | 0.9478 | 0.8684 | 0.9064 | 0.0363 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.50 | Lightweight Model Only | N/A | 0.9867 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.50 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.55 | Lightweight Model Only | 1.0000 | 0.4810 | 0.6496 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.55 | Hybrid / Full Pipeline | 1.0000 | 0.5063 | 0.6723 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.55 | Lightweight Model Only | 0.9943 | 0.8397 | 0.9105 | 0.0036 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.55 | Hybrid / Full Pipeline | 0.9462 | 0.8421 | 0.8911 | 0.0363 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.55 | Lightweight Model Only | N/A | 0.9800 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.55 | Hybrid / Full Pipeline | N/A | 0.9800 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.60 | Lightweight Model Only | 1.0000 | 0.3797 | 0.5505 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.60 | Hybrid / Full Pipeline | 1.0000 | 0.4177 | 0.5893 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.60 | Lightweight Model Only | 1.0000 | 0.8038 | 0.8912 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.60 | Hybrid / Full Pipeline | 0.9494 | 0.8086 | 0.8734 | 0.0327 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.60 | Lightweight Model Only | N/A | 0.9700 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.60 | Hybrid / Full Pipeline | N/A | 0.9700 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.65 | Lightweight Model Only | 1.0000 | 0.2278 | 0.3711 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.65 | Hybrid / Full Pipeline | 1.0000 | 0.2658 | 0.4200 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.65 | Lightweight Model Only | 1.0000 | 0.7656 | 0.8672 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.65 | Hybrid / Full Pipeline | 0.9472 | 0.7727 | 0.8511 | 0.0327 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.65 | Lightweight Model Only | N/A | 0.9600 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.65 | Hybrid / Full Pipeline | N/A | 0.9600 | N/A | N/A |  |
| `deepset/prompt-injections` | external-tuned | 0.70 | Lightweight Model Only | 1.0000 | 0.1646 | 0.2826 | 0.0000 |  |
| `deepset/prompt-injections` | external-tuned | 0.70 | Hybrid / Full Pipeline | 1.0000 | 0.2278 | 0.3711 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.70 | Lightweight Model Only | 1.0000 | 0.7321 | 0.8453 | 0.0000 |  |
| `protectai/prompt-injection-validation` | external-tuned | 0.70 | Hybrid / Full Pipeline | 0.9450 | 0.7392 | 0.8295 | 0.0327 |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.70 | Lightweight Model Only | N/A | 0.9467 | N/A | N/A |  |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.70 | Hybrid / Full Pipeline | N/A | 0.9500 | N/A | N/A |  |

## Interpretation

- F1이 계산 가능한 데이터셋은 F1을 우선하고, Precision 0.70 이상 후보를 선호한다.
- positive-only 데이터셋은 안전 negative가 없어 FP rate와 F1을 계산할 수 없으므로 Recall 중심으로만 추천한다.
- 추천 threshold는 운영 정책에 바로 고정하기보다 held-out eval 결과와 FP 증가 여부를 함께 검토하는 후보값이다.
