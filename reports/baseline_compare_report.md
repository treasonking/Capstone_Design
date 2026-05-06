# Baseline Comparison Report

## Dataset
- Path: `evaluation/sample_dataset.json`
- Size: 108

## Lightweight Model Status
- Enabled: false
- Status: dependency_missing
- Note: 선택 의존성이 없어 Lightweight Model Only는 unavailable로 표시되고 Hybrid는 regex/rule fallback으로 동작한다.

## Results

| Mode | Task | Precision | Recall | F1 | Accuracy | Status |
|---|---|---:|---:|---:|---:|---|
| Regex Only | pii | 1.000 | 1.000 | 1.000 | 1.000 | available |
| Rule Only | injection | 1.000 | 1.000 | 1.000 | 1.000 | available |
| Lightweight Model Only | pii | N/A | N/A | N/A | N/A | unavailable |
| Lightweight Model Only | injection | N/A | N/A | N/A | N/A | unavailable |
| Hybrid | pii | 1.000 | 1.000 | 1.000 | 1.000 | regex/rule fallback |
| Hybrid | injection | 1.000 | 1.000 | 1.000 | 1.000 | regex/rule fallback |