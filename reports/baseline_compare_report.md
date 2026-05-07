# Baseline Comparison Report

> 이 리포트는 동일한 내부 회귀 데이터셋에서 `regex only`, `rule only`, `lightweight model only`, `hybrid` 구성을 비교한 요약이다. 선택형 경량 분류기 artifact 또는 선택 의존성이 없는 환경에서는 `Lightweight Model Only`가 `N/A`로 표시될 수 있으며, 이 경우 `Hybrid`는 `regex/rule fallback` 상태로 해석해야 한다.

## Dataset

- Path: `evaluation/sample_dataset.json`
- Size: 113

## Detector Availability

| Item | Value |
|---|---|
| Lightweight model enabled | false |
| Lightweight model status | dependency_missing |
| Interpretation | 선택 의존성이 없어 `Lightweight Model Only`는 실행 불가이며, `Hybrid`는 `regex/rule fallback` 경로로 동작 |

## Results

| Mode | Task | Precision | Recall | F1 | Accuracy | Status |
|---|---|---:|---:|---:|---:|---|
| Regex Only | pii | 1.000 | 1.000 | 1.000 | 1.000 | available |
| Rule Only | injection | 1.000 | 1.000 | 1.000 | 1.000 | available |
| Lightweight Model Only | pii | N/A | N/A | N/A | N/A | unavailable |
| Lightweight Model Only | injection | N/A | N/A | N/A | N/A | unavailable |
| Hybrid | pii | 1.000 | 1.000 | 1.000 | 1.000 | regex/rule fallback |
| Hybrid | injection | 1.000 | 1.000 | 1.000 | 1.000 | regex/rule fallback |

## Reading Guide

- `N/A`는 성능이 0이라는 뜻이 아니라, 현재 실행 환경에서 선택형 경량 분류기 artifact 또는 의존성이 없어 해당 단독 모드를 평가하지 못했다는 뜻이다.
- `regex/rule fallback`은 하이브리드 구조가 실패한 것이 아니라, 선택형 분류기 없이도 기본 detector 경로로 계속 동작했다는 뜻이다.
- 따라서 이 표는 "선택형 분류기 단독 성능 우위"를 보여주는 자료가 아니라, 현재 MVP가 artifact 부재 상황에서도 회귀 테스트를 안정적으로 통과하는지 확인하는 운영형 비교표로 해석해야 한다.
