# External Threshold Sweep

- Generated at: `2026-05-18T18:38:50`
- Hugging Face split: `all`
- Thresholds: `0.30, 0.40, 0.50, 0.60, 0.70`

## Model Status

| Item | Value |
|---|---|
| enabled | True |
| status | enabled |
| note | Lightweight model loaded. |
| vectorizer_path | C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\vectorizer.joblib |
| classifier_path | C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\classifier.joblib |

## Results

| Dataset | Threshold | Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | 0.30 | Lightweight Model Only | 0.4446 | 0.9316 | 0.6020 | 0.5106 | 245 | 306 | 93 | 18 |
| `deepset/prompt-injections` | 0.30 | Hybrid / Full Pipeline | 0.4446 | 0.9316 | 0.6020 | 0.5106 | 245 | 306 | 93 | 18 |
| `protectai/prompt-injection-validation` | 0.30 | Lightweight Model Only | 0.4634 | 0.9720 | 0.6276 | 0.5023 | 1353 | 1567 | 268 | 39 |
| `protectai/prompt-injection-validation` | 0.30 | Hybrid / Full Pipeline | 0.4634 | 0.9720 | 0.6276 | 0.5023 | 1353 | 1567 | 268 | 39 |
| `Lakera/gandalf_ignore_instructions` | 0.30 | Lightweight Model Only | N/A | 0.9850 | N/A | 0.9850 | 985 | N/A | N/A | 15 |
| `Lakera/gandalf_ignore_instructions` | 0.30 | Hybrid / Full Pipeline | N/A | 0.9850 | N/A | 0.9850 | 985 | N/A | N/A | 15 |
| `deepset/prompt-injections` | 0.40 | Lightweight Model Only | 0.5219 | 0.7719 | 0.6227 | 0.6284 | 203 | 186 | 213 | 60 |
| `deepset/prompt-injections` | 0.40 | Hybrid / Full Pipeline | 0.5219 | 0.7719 | 0.6227 | 0.6284 | 203 | 186 | 213 | 60 |
| `protectai/prompt-injection-validation` | 0.40 | Lightweight Model Only | 0.4846 | 0.9246 | 0.6359 | 0.5432 | 1287 | 1369 | 466 | 105 |
| `protectai/prompt-injection-validation` | 0.40 | Hybrid / Full Pipeline | 0.4846 | 0.9246 | 0.6359 | 0.5432 | 1287 | 1369 | 466 | 105 |
| `Lakera/gandalf_ignore_instructions` | 0.40 | Lightweight Model Only | N/A | 0.9730 | N/A | 0.9730 | 973 | N/A | N/A | 27 |
| `Lakera/gandalf_ignore_instructions` | 0.40 | Hybrid / Full Pipeline | N/A | 0.9730 | N/A | 0.9730 | 973 | N/A | N/A | 27 |
| `deepset/prompt-injections` | 0.50 | Lightweight Model Only | 0.8247 | 0.3042 | 0.4444 | 0.6979 | 80 | 17 | 382 | 183 |
| `deepset/prompt-injections` | 0.50 | Hybrid / Full Pipeline | 0.8300 | 0.3156 | 0.4573 | 0.7024 | 83 | 17 | 382 | 180 |
| `protectai/prompt-injection-validation` | 0.50 | Lightweight Model Only | 0.6404 | 0.7651 | 0.6972 | 0.7134 | 1065 | 598 | 1237 | 327 |
| `protectai/prompt-injection-validation` | 0.50 | Hybrid / Full Pipeline | 0.6342 | 0.7672 | 0.6944 | 0.7087 | 1068 | 616 | 1219 | 324 |
| `Lakera/gandalf_ignore_instructions` | 0.50 | Lightweight Model Only | N/A | 0.9030 | N/A | 0.9030 | 903 | N/A | N/A | 97 |
| `Lakera/gandalf_ignore_instructions` | 0.50 | Hybrid / Full Pipeline | N/A | 0.9040 | N/A | 0.9040 | 904 | N/A | N/A | 96 |
| `deepset/prompt-injections` | 0.60 | Lightweight Model Only | 1.0000 | 0.0798 | 0.1479 | 0.6344 | 21 | 0 | 399 | 242 |
| `deepset/prompt-injections` | 0.60 | Hybrid / Full Pipeline | 1.0000 | 0.1255 | 0.2230 | 0.6526 | 33 | 0 | 399 | 230 |
| `protectai/prompt-injection-validation` | 0.60 | Lightweight Model Only | 0.8990 | 0.3261 | 0.4787 | 0.6935 | 454 | 51 | 1784 | 938 |
| `protectai/prompt-injection-validation` | 0.60 | Hybrid / Full Pipeline | 0.8560 | 0.3930 | 0.5387 | 0.7096 | 547 | 92 | 1743 | 845 |
| `Lakera/gandalf_ignore_instructions` | 0.60 | Lightweight Model Only | N/A | 0.6870 | N/A | 0.6870 | 687 | N/A | N/A | 313 |
| `Lakera/gandalf_ignore_instructions` | 0.60 | Hybrid / Full Pipeline | N/A | 0.7450 | N/A | 0.7450 | 745 | N/A | N/A | 255 |
| `deepset/prompt-injections` | 0.70 | Lightweight Model Only | 1.0000 | 0.0038 | 0.0076 | 0.6042 | 1 | 0 | 399 | 262 |
| `deepset/prompt-injections` | 0.70 | Hybrid / Full Pipeline | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 |
| `protectai/prompt-injection-validation` | 0.70 | Lightweight Model Only | 1.0000 | 0.0136 | 0.0269 | 0.5745 | 19 | 0 | 1835 | 1373 |
| `protectai/prompt-injection-validation` | 0.70 | Hybrid / Full Pipeline | 0.8399 | 0.1997 | 0.3227 | 0.6384 | 278 | 53 | 1782 | 1114 |
| `Lakera/gandalf_ignore_instructions` | 0.70 | Lightweight Model Only | N/A | 0.1110 | N/A | 0.1110 | 111 | N/A | N/A | 889 |
| `Lakera/gandalf_ignore_instructions` | 0.70 | Hybrid / Full Pipeline | N/A | 0.4680 | N/A | 0.4680 | 468 | N/A | N/A | 532 |

## Observed Conclusion

- 현재 0.70 threshold에서는 Lightweight Model Only Recall이 매우 낮아 Hybrid가 Rule Only와 거의 같게 보인다.
- threshold를 0.30 또는 0.40으로 낮추면 Recall은 크게 상승하지만 `deepset`과 `protectai`에서 FP도 크게 증가한다.
- 따라서 원인은 단순히 모델이 항상 영어 공격을 못 알아보는 것이 아니라, 현재 classifier confidence calibration과 운영 threshold가 외부 영어 데이터셋에 맞지 않는 데 있다.
- 운영용 threshold를 무작정 낮추기보다는 외부 영어 데이터 기반 재학습, validation split 기반 threshold 조정, hard negative 보강이 필요하다.

## Interpretation

- threshold를 낮췄을 때 Lightweight Model Only Recall이 크게 상승하면 기존 threshold가 너무 보수적이었을 가능성이 있다.
- threshold를 낮춰도 Recall이 거의 상승하지 않으면 모델 자체가 영어 공격 표현을 충분히 학습하지 못한 것이다.
- threshold를 낮췄을 때 FP가 급증하면 운영 threshold는 보수적으로 유지하고, 외부 영어 데이터 기반 재학습을 우선 검토한다.
