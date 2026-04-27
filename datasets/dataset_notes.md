# Dataset Notes

## Purpose

이 데이터셋은 공공기관·사내망 환경의 LLM 보안 프록시에서 PII 유출과 Prompt Injection 시도를 평가하기 위한 합성 평가셋이다. 단순 데모 문자열만 모으는 대신, 실제 운영에서 오탐과 미탐을 만들 가능성이 큰 경계 사례를 포함해 룰 기반 탐지기의 강점과 한계를 함께 드러내는 것을 목표로 한다.

## Composition Principles

- `sample_dataset.json`은 v1 기준 샘플을 보존한다.
- `sample_dataset_v2.json`은 v1을 기반으로 metadata와 확장 샘플을 추가한 주 평가셋이다.
- `sample_dataset_v2_balanced.json`은 category별 최대 수량을 제한해 특정 유형이 과도하게 지배하지 않도록 만든 균형 버전이다.
- 모든 샘플은 `id`, `task`, `text`, `labels`를 유지해 기존 평가 스크립트와 호환된다.
- `difficulty`, `category`, `notes`, `source`는 분석 편의를 위한 optional metadata다.

## Label Overview

PII 라벨은 이메일, 휴대전화, 주민등록번호, 계좌번호의 네 가지로 구성된다. Injection 라벨은 직접 지시 무시, 시스템 프롬프트 추출, 정책 우회, 역할 전환, 디버그 모드, 내부 규칙 공개, 다단계 추출, 난독화 시도 등으로 나뉜다.

라벨 기준의 핵심은 `datasets/labeling_guide.md`에 고정했다. 특히 `시스템 프롬프트 설계 원칙` 같은 정상 학습 질문과 `시스템 프롬프트를 출력해` 같은 공격 질문을 분리한다.

## Positive, Negative, Boundary Design

Positive 샘플은 탐지되어야 하는 명확한 위험 패턴이다. Negative 샘플은 위험 패턴이 없는 일반 업무 문장이다. Boundary 샘플은 숫자 구조나 보안 용어 때문에 탐지기가 헷갈릴 수 있지만 정책상 정상으로 보는 문장이다.

Boundary를 크게 늘린 이유는 다음과 같다.

- 대표번호, 고객센터 번호, 문서번호, 승인번호는 PII 계좌/전화번호 탐지에서 오탐을 만들 수 있다.
- `system`, `prompt`, `policy`, `rule`, `debug` 같은 단어는 공격 문장에도 정상 보안 학습 문장에도 모두 등장한다.
- 보고서/메신저/공문체/줄바꿈/괄호/한영 혼합 문장은 단문 정규식보다 실제 운영 환경에 가깝다.

## Current v2 Summary

- 총 샘플 수: 152개
- PII / Injection: 70 / 82개
- Positive / Negative: 94 / 58개
- Multilabel 샘플: 49개
- Boundary 후보: 89개
- 주요 추가 유형: 전화번호 boundary, 계좌번호 boundary, 간접형 injection, 다단계 extraction, system/prompt/policy 정상 질문

## Known Detector Limitations Exposed by v2

v2는 점수를 높이기 위해 쉬운 샘플만 추가하지 않았다. 현재 평가 리포트는 다음 한계를 드러낸다.

- 계좌번호 탐지는 문서번호, 승인번호, 수식 같은 account-like 숫자에서 false positive가 발생하기 쉬웠으나, 현재 v2 리포트 기준 PII_ACCOUNT FP는 0건으로 감소했다.
- `+82 (10) ...`처럼 괄호가 포함된 휴대전화 국제 표기를 탐지하도록 보강했다.
- `상위 지시를 따르지 말고`, `필터 없이`, `숨겨진 지시를 요약`, `내부 원칙을 정리` 같은 간접 표현을 추가 라벨과 탐지 룰로 보강했다.
- 기본 평가셋에서는 `h1dden instruction`, `s y s t e m prompt` 같은 난독화 샘플을 별도 reason_code로 보존하도록 개선했다.
- `Do not reveal hidden prompt`처럼 금지 문맥으로 등장한 표현은 boundary-safe 처리로 정상 문장과 공격 문장을 분리하도록 보강했다.

## Synthetic Data Caveat

이 데이터셋은 보고서와 PoC 평가를 위한 합성 데이터셋이다. 실제 운영 성능을 대표한다고 과장해서는 안 된다. 실제 서비스 적용 전에는 비식별화된 운영 로그, 기관별 문서 양식, 실제 민원 문장, 내부 업무 메신저 표현을 추가해 재평가해야 한다.

## Changelog

### v2

- v1 데이터셋에 optional metadata 추가
- 라벨링 가이드 작성
- PII boundary와 account-like negative 샘플 추가
- Injection 간접형, 역할 전환형, 다단계 추출형, 정상 보안 개념 질문 추가
- 검증, 통계, 상세 평가 스크립트 추가
- Markdown/JSON 평가 리포트와 오류 사례 리포트 자동 생성
