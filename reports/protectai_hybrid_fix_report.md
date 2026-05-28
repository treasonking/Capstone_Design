# protectai Hybrid Fusion Fix Report

- Generated at: `2026-05-29T00:48:04`
- Evaluation threshold: `0.30`
- Medium-rule model-support threshold: `0.45`

## Before

| Mode | Precision | Recall | F1 | TP / FP / FN |
|---|---:|---:|---:|---|
| Rule Only | 0.8448 | 0.2344 | 0.3670 | 98 / 18 / 320 |
| Model Only | 0.9946 | 0.8876 | 0.9381 | 371 / 2 / 47 |
| Hybrid | 0.9488 | 0.8876 | 0.9172 | 371 / 20 / 47 |

## After

| Mode | Precision | Recall | F1 | TP / FP / FN |
|---|---:|---:|---:|---|
| Rule Only | 0.8448 | 0.2344 | 0.3670 | 98 / 18 / 320 |
| Model Only | 0.9946 | 0.8876 | 0.9381 | 371 / 2 / 47 |
| Hybrid Calibrated | 0.9946 | 0.8876 | 0.9381 | 371 / 2 / 47 |

## Interpretation

The previous Hybrid pipeline underperformed Model Only on the protectai dataset because the rule layer increased false positives without reducing false negatives. The calibrated fusion logic reduces rule-only over-triggering by allowing only high-severity rules to override the model prediction and requiring model support for medium-severity rules.

protectai/prompt-injection-validation 데이터셋에서 초기 Hybrid 파이프라인은 Lightweight Model Only보다 낮은 F1을 보였다. 원인 분석 결과, Hybrid는 Model Only와 동일한 TP/FN을 기록했지만 FP가 2건에서 20건으로 증가하였다. 이는 Rule 계층이 해당 데이터셋에서 모델이 놓친 공격을 추가로 복구하지 못하고, 일부 정상 샘플을 위험으로 오탐했기 때문이다. 따라서 본 시스템의 Hybrid 구조는 모든 벤치마크에서 단일 모델보다 우수한 분류기로 해석하기보다, 개인정보 탐지, 정책 결정, reason_code, 감사 가능성을 결합한 운영형 보안 파이프라인으로 해석한다.

## Follow-up Interpretation

Hybrid Calibrated가 Model Only와 동일한 `371 / 2 / 47`로 회복된 것은 Hybrid가 Model Only보다 우수해졌다는 의미가 아니다. 이 결과는 prompt-injection-only benchmark에서 rule-only override를 보정해 기존 Hybrid OR 결합이 만들던 불필요한 FP 증가를 억제했다는 의미로 해석한다.

운영 환경에서는 Hybrid가 PII 탐지, 정책 조치, reason_code, audit summary를 함께 제공하므로 단일 benchmark F1만으로 구조 전체의 목적을 평가하지 않는다. 반대로 prompt-injection-only 벤치마크에서는 PII rule과 낮은 severity injection keyword가 최종 positive prediction에 섞이지 않도록 별도 fusion 기준을 유지한다.
