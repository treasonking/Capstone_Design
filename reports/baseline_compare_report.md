# Baseline Comparison Report

- Status: Placeholder report
- Expected command: `python -m evaluation.baseline_compare --dataset evaluation/sample_dataset.json --report reports/baseline_compare_report.md`
- Expected fallback behavior: if model artifacts are missing, `Lightweight Model Only` should be reported as unavailable and `Hybrid` should fall back to regex/rule detections.
- Verification note: `2026-05-05` 작업 셸에서는 `python` 명령이 없고 `py -0` 결과가 `No Installed Pythons Found!`여서 보고서를 재생성하지 못했습니다.

이 보고서는 Python 런타임과 선택 의존성(`pip install ".[dev,perf]"`)이 준비된 환경에서 다시 생성해야 합니다.
