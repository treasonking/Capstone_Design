# Paper Baseline Comparison

## Dataset Coverage

| Method | Evaluation scope | Input rows | Result rows | Error count |
|---|---|---:|---:|---:|
| Attention Tracker | Capstone selected dataset | 100 | 75 | 25 |
| Our Capstone Hybrid Proxy | Full capstone selected dataset | 100 | 100 | 0 |
| Our Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | 75 | 75 | 0 |

## Quantitative Results

| Method | Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---:|---:|---:|---:|---:|
| Attention Tracker | Successful rows only | 0.7600 | 0.6522 | 0.9375 | 0.7692 | 0.9208 |
| Our Capstone Hybrid Proxy | Same successful rows as Attention Tracker | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A |
| Our Capstone Hybrid Proxy | Full 100 rows | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A |
| Attention Tracker | Paper-reported deepset | N/A | N/A | N/A | N/A | 0.98 |

## Interpretation

Attention Tracker local metrics are computed only on successfully evaluated rows.

Because 25 out of 100 rows initially failed due to local runtime constraints, the 75-row local result must not be interpreted as full-dataset performance.

Our Capstone Hybrid Proxy is additionally evaluated on the full 100-row selected dataset.

The matched subset comparison is included only for method-to-method comparison under identical row coverage.

Attention Tracker's paper-reported AUROC 0.98 is not a local reproduction result.

The local Attention Tracker AUROC 0.9208 uses inverted focus scores: `attack_score = -focus_score`.

Our Capstone Hybrid Proxy's matched deepset subset F1 0.1176 is an external baseline result showing limitations on English public prompt-injection datasets. The full 100-row deepset subset F1 is 0.0870. These results should be interpreted separately from the project's internal public-sector and PII-specialized evaluation results.
