# External Benchmark Discussion

## Why external benchmark performance is lower than internal regression performance

내부 회귀 테스트에서는 프로젝트에서 정의한 정책 위반 유형과 공공기관 시나리오 기반 공격 문장을 중심으로 평가했기 때문에 높은 성능이 확인되었다. 반면 외부 공개 데이터셋은 영어 기반 일반 Prompt Injection 문장, 다양한 우회 표현, 데이터셋별 공격 패턴을 포함하고 있어 현재 rule/heuristic 중심 탐지기의 커버리지가 충분하지 않았다.

따라서 외부 데이터셋에서 낮은 Recall과 F1-score가 나온 것은 현재 탐지기의 일반화 한계를 보여준다. 이 결과는 프로젝트 실패가 아니라, 향후 개선 방향을 정량적으로 제시하는 근거로 활용한다.

## How this result will be used

외부 벤치마크 결과는 다음 개선 작업의 기준선으로 사용한다.

1. 영어 기반 Prompt Injection 패턴 추가
2. 한국어/영어 혼합 우회 표현 추가
3. `ignore`, `override`, `disregard`, `reveal`, `system prompt`, `developer message` 계열 표현 보강
4. Rule Only와 Hybrid Detector 성능 분리 측정
5. Lightweight classifier를 실제로 활성화한 상태에서 재평가
6. 공개 데이터셋 기반 회귀 테스트 자동화

## Presentation answer

외부 공개 데이터셋 평가 결과 내부 데이터셋보다 낮은 성능이 확인되었다. 이는 현재 시스템이 공공기관·사내망 환경의 정책 우회 및 개인정보 유출 시나리오에 초점을 맞춘 rule/heuristic 기반 구조이기 때문이다. 공개 데이터셋 결과는 일반화 성능의 한계를 확인하기 위한 기준선이며, 향후 경량 분류기 학습과 다국어 우회 패턴 보강의 근거로 활용한다.
