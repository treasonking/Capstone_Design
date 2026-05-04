# Performance Report

- Generated at: 2026-05-04T23:01:30
- Scope: current internal/local benchmark and evidence scan only. This does not guarantee production performance.

## Summary Metrics

| Metric | Value |
|---|---:|
| Total Requests | 1200 |
| Failures | 6 |
| Error Rate | 0.50% |
| Average Latency | 142.30 ms |
| p95 Latency | 318.40 ms |
| Requests/sec | 48.75 |
| Scanned Files | 2 |
| Sensitive Findings | 0 |

## PASS / FAIL Criteria

| Criterion | Actual | Threshold | Status |
|---|---:|---:|---|
| Error Rate <= 1.00% | 0.50% | 1.00% | PASS |
| p95 Latency <= 500ms | 318.40 ms | 500.00 ms | PASS |
| Sensitive Findings == 0 | 0 | 0 | PASS |

## Notes

- Locust summary values come from `performance/proxy_load_stats.csv`.
- Sensitive findings come from the masked JSON output of `tools/scanner.py`.
- This report is intended for capstone presentation and local reproducibility evidence.