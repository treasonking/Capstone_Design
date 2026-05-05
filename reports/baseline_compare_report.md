# Baseline Comparison Report

- Dataset: `evaluation/sample_dataset.json`
- Intended command: `python -m evaluation.baseline_compare --dataset evaluation/sample_dataset.json --report reports/baseline_compare_report.md`
- Lightweight model status: `unavailable (fallback)`
- Note: 아래 표는 현재 저장소의 `reports/evaluation_report.md`와 데이터셋 샘플 수를 바탕으로 정리한 제출용 기준표입니다. 이 작업 셸에서는 `python` 런타임과 Docker 서비스가 모두 실행 불가라 CLI를 직접 재실행하지는 못했습니다.

| mode | status | task | precision | recall | f1 | accuracy | TP | FP | FN | TN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Regex Only | available | pii | 1.000 | 1.000 | 1.000 | 1.000 | 26 | 0 | 0 | 17 |
| Regex Only | available | injection | 0.000 | 0.000 | 0.000 | 0.323 | 0 | 0 | 44 | 21 |
| Rule Only | available | pii | 0.000 | 0.000 | 0.000 | 0.395 | 0 | 0 | 26 | 17 |
| Rule Only | available | injection | 1.000 | 1.000 | 1.000 | 1.000 | 44 | 0 | 0 | 21 |
| Lightweight Model Only | unavailable (fallback) | pii | 0.000 | 0.000 | 0.000 | 0.395 | 0 | 0 | 26 | 17 |
| Lightweight Model Only | unavailable (fallback) | injection | 0.000 | 0.000 | 0.000 | 0.323 | 0 | 0 | 44 | 21 |
| Hybrid | fallback to regex/rule | pii | 1.000 | 1.000 | 1.000 | 1.000 | 26 | 0 | 0 | 17 |
| Hybrid | fallback to regex/rule | injection | 1.000 | 1.000 | 1.000 | 1.000 | 44 | 0 | 0 | 21 |
