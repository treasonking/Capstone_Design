# Multi-layered Detection Ablation Report

> 이 리포트는 동일한 내부 회귀 데이터셋에서 다층형 탐지 파이프라인의 계층별 기여도를 비교한 요약이다. 현재 보고서는 경량 분류 계층 artifact 또는 의존성이 없는 환경에서 실행되었기 때문에 Lightweight Classification Layer only 결과는 `N/A`로 표시된다. 따라서 이 보고서는 최종 계층별 성능 비교가 아니라, 현재 MVP가 경량 분류 계층 비활성화 상황에서도 Regex Pattern Layer와 Heuristic Rule Layer를 통해 안정적으로 동작하는지 확인하는 중간 보고서이다.

## Dataset

- Path: `evaluation/sample_dataset.json`
- Size: 113

## Ablation Groups

| Group | Configuration | Purpose |
|---|---|---|
| A | Regex Pattern Layer only | 정규식 계층이 정형 PII 탐지에서 얼마나 효과적인지 확인한다. |
| B | Heuristic Rule Layer only | 휴리스틱 규칙 계층이 프롬프트 인젝션 탐지 성능에 얼마나 기여하는지 확인한다. |
| C | Lightweight Classification Layer only | 경량 분류 계층이 비정형 공격 탐지에 기여하는지 확인한다. |
| D | Regex Pattern Layer + Heuristic Rule Layer | 정형 PII와 명시적 인젝션 단서 결합 시 탐지 안정성을 확인한다. |
| E | Full Multi-layered Detection Pipeline | 최종 다층형 구조가 단일 계층 구조보다 Recall과 안정성을 높이는지 확인한다. |

향후 최종 비교에서는 경량 분류 계층 artifact를 생성한 뒤 다음 실험군을 모두 비교한다.

1. A. Regex Pattern Layer only
2. B. Heuristic Rule Layer only
3. C. Lightweight Classification Layer only
4. D. Regex Pattern Layer + Heuristic Rule Layer
5. E. Full Multi-layered Detection Pipeline

## Lightweight Classification Layer Status

| Item | Value |
|---|---|
| Lightweight classification layer enabled | false |
| Lightweight classification layer status | dependency_missing |
| Interpretation | 경량 분류 계층 artifact 또는 의존성이 없어 `Lightweight Classification Layer only`는 실행 불가이며, Full Multi-layered Pipeline은 `regex+heuristic fallback` 경로로 동작 |

## Results

| Mode | Task | Precision | Recall | F1 | Accuracy | Status |
|---|---|---:|---:|---:|---:|---|
| A. Regex Pattern Layer only | pii | 1.000 | 1.000 | 1.000 | 1.000 | available |
| B. Heuristic Rule Layer only | injection | 1.000 | 1.000 | 1.000 | 1.000 | available |
| C. Lightweight Classification Layer only | pii | N/A | N/A | N/A | N/A | unavailable |
| C. Lightweight Classification Layer only | injection | N/A | N/A | N/A | N/A | unavailable |
| D. Regex Pattern Layer + Heuristic Rule Layer | pii | 1.000 | 1.000 | 1.000 | 1.000 | available |
| D. Regex Pattern Layer + Heuristic Rule Layer | injection | 1.000 | 1.000 | 1.000 | 1.000 | available |
| E. Full Multi-layered Pipeline | pii | 1.000 | 1.000 | 1.000 | 1.000 | regex+heuristic fallback |
| E. Full Multi-layered Pipeline | injection | 1.000 | 1.000 | 1.000 | 1.000 | regex+heuristic fallback |

## Reading Guide

- `N/A`는 성능이 0이라는 뜻이 아니라, 현재 실행 환경에서 경량 분류 계층 artifact 또는 모델 의존성이 없어 해당 단독 모드를 평가하지 못했다는 뜻이다.
- `regex+heuristic fallback`은 전체 파이프라인이 실패한 것이 아니라, 경량 분류 계층 artifact가 없는 환경에서도 정규식 패턴 계층과 휴리스틱 규칙 계층 중심으로 계속 동작했다는 뜻이다.
- 따라서 이 표는 경량 분류 계층 단독 성능 우위를 보여주는 자료가 아니라, 현재 MVP가 artifact 부재 상황에서도 회귀 테스트를 안정적으로 통과하는지 확인하는 운영형 비교표로 해석해야 한다.
