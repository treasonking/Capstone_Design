# Deepset Official Split Comparison

- Generated at: `2026-05-18T22:08:45`
- Lightweight threshold: `0.30`

| Split Policy | Dataset | Model Version | Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| custom 70/30 eval | `deepset/prompt-injections` | external-tuned | Rule Only | 1.0000 | 0.0886 | 0.1628 | 0.6382 | 7 | 0 | 120 | 72 |
| custom 70/30 eval | `deepset/prompt-injections` | external-tuned | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.8442 | 48 | 0 | 120 | 31 |
| custom 70/30 eval | `deepset/prompt-injections` | external-tuned | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.8543 | 50 | 0 | 120 | 29 |
| official train/test | `deepset/prompt-injections` | deepset-official-train | Rule Only | 1.0000 | 0.0500 | 0.0952 | 0.5086 | 3 | 0 | 56 | 57 |
| official train/test | `deepset/prompt-injections` | deepset-official-train | Lightweight Model Only | 1.0000 | 0.7833 | 0.8785 | 0.8879 | 47 | 0 | 56 | 13 |
| official train/test | `deepset/prompt-injections` | deepset-official-train | Hybrid / Full Pipeline | 1.0000 | 0.7667 | 0.8679 | 0.8793 | 46 | 0 | 56 | 14 |

## Interpretation

Official test split performance did not drop below the custom split result. This supports that the deepset improvement is not explained solely by the custom 70/30 split, although near-duplicate findings still require cautious wording.

- `custom 70/30 eval` uses the project-generated held-out eval split and the saved `external-tuned` artifact.
- `official train/test` trains a temporary lightweight model with internal samples plus deepset official train split, then evaluates deepset official test split.
- If custom split performance is much higher than official test performance, custom split metrics may be easier or inflated by similar examples.
