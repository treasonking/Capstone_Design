# Hybrid Detection Evaluation Report

이 파일은 새 하이브리드 평가 파이프라인용 placeholder입니다.

현재 셸 환경에서는 Python 런타임이 감지되지 않아 `evaluation/evaluate_detection.py`를 실제 실행하지 못했습니다. 따라서 이전 룰 기반 MVP 수치를 그대로 재사용하지 않고, 아래 명령으로 새 평가 결과를 재생성하도록 상태를 초기화해 두었습니다.

```bash
python evaluation/evaluate_detection.py --mode regex
python evaluation/evaluate_detection.py --mode rule
python evaluation/evaluate_detection.py --mode model
python evaluation/evaluate_detection.py --mode hybrid
```

실행 후 함께 갱신되는 파일:

- `reports/evaluation_summary.json`
- `reports/false_positives.csv`
- `reports/false_negatives.csv`
- `reports/confusion_matrix.csv`
