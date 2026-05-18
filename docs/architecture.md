# 다층형 탐지 파이프라인 아키텍처

본 시스템은 다층형 탐지 파이프라인(Multi-layered Detection Pipeline)을 기반으로 한다. 여러 탐지기를 단순히 병렬 실행하는 구조가 아니라, 정규식 패턴 계층, 휴리스틱 규칙 계층, 경량 분류 계층, 의사결정 계층을 순차적으로 통과하며 각 계층의 결과를 다음 판단에 반영한다.

## 계층 구성

| 계층 | 명칭 | 목적 | 주요 탐지 대상 |
|---|---|---|---|
| 1 | 정규식 패턴 계층 | 형식이 명확한 개인정보를 빠르게 탐지 | 주민등록번호, 전화번호, 이메일, 계좌번호 |
| 2 | 휴리스틱 규칙 계층 | 키워드 조합과 문맥 단서를 기반으로 위험 판단 | 정책 우회, 시스템 프롬프트 탈취, 지시 무시 |
| 3 | 경량 분류 계층 | 패턴 기반으로 탐지하기 어려운 문장형 공격 분류 | 우회형 인젝션, 문맥형 공격, 애매한 악성 지시 |
| 4 | 의사결정 계층 | 각 계층의 탐지 결과를 종합하여 정책 적용 | ALLOW, MASK, BLOCK, WARN |

## 탐지 순서

1. 입력 요청을 수신한다.
2. Regex Pattern Layer에서 정형 PII를 우선 탐지한다.
3. Heuristic Rule Layer에서 프롬프트 인젝션 키워드, 정책 우회 문장, 조합 규칙을 탐지한다.
4. Lightweight Classification Layer에서 비정형 또는 애매한 문장을 분류한다.
5. Decision Layer에서 탐지 결과를 종합하여 최종 action을 결정한다.
6. action이 `MASK`이면 민감정보를 치환한 뒤 upstream LLM으로 전달한다.
7. action이 `BLOCK`이면 upstream LLM 호출 없이 차단 응답을 반환한다.
8. action이 `ALLOW`이면 요청을 그대로 upstream LLM으로 전달한다.
9. LLM 또는 Mock LLM 응답 생성 이후 Validator Agent가 최종 사용자 반환 전에 출력을 재검사한다.
10. Validator Agent는 출력 내 PII 잔존, 시스템 프롬프트 또는 내부 정책 노출, 정책 우회 성공 징후, 마스킹 누락을 검사한다.
11. 최종 응답 이후 audit log에는 `input_action`, `output_action`, `final_action`, Validator Agent 결과가 분리 기록되고, PQC-compatible integrity signature가 추가된다.

## 구현 메모

현재 코드에는 기존 구현 호환성을 위해 `backend/app/detection/hybrid_detector.py`와 `hybrid_detection` audit 필드명이 남아 있다. 문서상 대표 명칭은 다층형 탐지 파이프라인이며, 본 시스템은 정책·패턴 기반 탐지와 경량 분류를 결합한다는 점에서 넓은 의미의 하이브리드 구조로만 설명한다.

Validator Agent는 입력 검사 전에 배치하지 않는다. 입력 검사는 detector와 policy engine이 담당하고, Validator Agent는 LLM 출력 생성 이후에만 실행되는 출력 검증 계층이다.

PQC는 탐지 성능 개선이 아니라 감사 로그 무결성 보호를 위한 확장 기능이다. 현재 개발 구현은 `MOCK-ML-DSA` signer를 사용하며, 운영 환경에서는 실제 ML-DSA signer로 교체할 수 있도록 인터페이스를 분리한다.
