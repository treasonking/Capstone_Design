# PrivacyGuard 보안 모델·주민센터 Agent 로드맵

## 구성요소와 책임

| 계층 | 현재 상태와 책임 |
|---|---|
| 입력 PII 탐지 | 정규식은 원문 위치를 찾아 마스킹에 사용한다. 경량 ML과 선택적 로컬 Ollama는 보조 신호를 낸다. |
| 프롬프트 인젝션 탐지 | 정규식·경량 ML·선택적 로컬 Ollama가 인젝션 신호를 낸다. 파인튜닝 모델은 이후 교체 후보로 평가한다. |
| 정책 엔진 | 탐지 신호를 종합해 ALLOW/MASK/BLOCK/WARN을 결정한다. 송신 직전 가드가 마스킹과 외부 전송 준비를 다시 확인한다. |
| 주민센터 Agent | 검사된 질문으로 공개자료를 검색하고 기존 Provider로 답변을 생성한다. |
| Validator Agent | Provider 또는 Mock 응답이 생성된 후 반환 전에 출력을 검증한다. SSE는 전체를 버퍼링한 후 검사한다. `/proxy/analyze`는 사전 분석이라 출력 검사가 `SKIPPED`일 수 있다. |
| 감사 로그와 Mock PQC | 감사 로그는 검사·정책 메타데이터를 보관한다. ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조를 사용한다. raw prompt, raw response, API key, system prompt, 개인정보 원문은 저장 금지 대상이다. |

## 단계별 산출물

| 단계 | 산출물과 다음 단계 진입 기준 |
|---|---|
| 1. 분석과 설계 | [탐지 진단](../training/detection_failure_analysis.md), [학습 환경](../training/training_environment_report.md), [데이터 설계](../training/dataset_design.md), [파인튜닝과 평가](../training/finetuning_plan.md), [Agent 개선안](../agent/resident_center_agent_upgrade_plan.md). |
| 2. 데이터 구축 | 레이블 지침 합의, 출처·권리 검토, 기존 평가 제외 목록 확정 후 데이터 제작과 이중 검수. 그룹 분할 및 독립 Holdout 봉인 후 manifest 고정. |
| 3. 파인튜닝 | 분리 환경에서 CUDA·모델 로딩·1 step 스모크 통과 후 QLoRA 또는 LoRA 실행. 어댑터·설정·해시를 보존. |
| 4. 비교 평가 | 동일 입력의 여섯 실험군과 라우팅 대조군을 재현. 정상 차단, 미탐, 송신 잔존을 함께 보고. |
| 5. 적응형 통합 | 비교 결과를 바탕으로 모델과 라우팅 후보를 선택. 로컬 GGUF 배포, API 계약, 장애 시 정책, 지연 및 자원 사용 회귀 검증. |
| 6. 주민센터 Agent | 공개자료와 업무별 검색을 확장하고 근거 일치·최신성·업무 효용·개인정보 보호를 검증. |

Phase 2부터는 별도 지시로 진행한다. 운영 변경의 채택 기준은 Phase 4 전에 정하고 내부 회귀, 외부 진단 및 독립 Holdout 결과를 각각 보고한다.
