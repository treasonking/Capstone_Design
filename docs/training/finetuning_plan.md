# 보안 Qwen 파인튜닝 및 비교 평가 계획

## Phase 3 학습

HF `Qwen/Qwen2.5-1.5B-Instruct` 원본 safetensors, 토크나이저와 chat template의 revision을 고정한다. [데이터 설계](dataset_design.md)의 두 필드를 정답으로 변환한다. HF 원본 모델 라이선스 표기는 Apache-2.0이다. [Qwen 모델 카드](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)

| 설정 | 초기 실험 후보 |
|---|---|
| 방식 | NF4 4-bit QLoRA + FP16 compute 우선, 환경 실측 뒤 FP16 LoRA 대체 |
| Micro batch / 누적 | 1 / 8 또는 16 |
| 입력 길이 | 256에서 시작, 여유와 커버리지를 확인해 512 비교 |
| LoRA | rank 8에서 시작, 16과 비교. Qwen 모듈 이름을 확인해 attention projection부터 시작하고 대상 목록을 기록 |
| 학습량 | 1~3 epochs 후보, validation에서 사전 정의한 탐지·구조 검증 기준으로 checkpoint 선택 |
| 메모리 | gradient checkpointing 지원 시 사용, 학습 시 KV cache 끔. SDPA/eager, native BF16·FlashAttention-2 비활성 |

Phase 1의 Windows QLoRA 스모크에서 rank 8, 길이 256, 배치 1의 GPU 어댑터 업데이트를 확인했다. 실제 길이 분포와 TRL 학습 루프는 Phase 3 진입 시 검증한다. [스모크와 메모리 측정](training_environment_report.md)

TRL conversational prompt-completion 형식으로 system/user는 prompt, assistant JSON만 completion에 둔다. completion-only mask와 EOS, 패딩, 정규화 및 실제 템플릿 결과를 소규모 배치에서 검사한다. Qwen2.5 템플릿의 assistant mask 동작은 버전마다 확인한다. 길이를 넘는 행은 탐지 단서·JSON·EOS가 잘리지 않도록 격리하고 언어·라벨별 비율을 보고한다. [TRL SFT 문서](https://huggingface.co/docs/trl/sft_trainer)

학습 설정과 seed, 데이터·템플릿·토크나이저 해시, Python 및 패키지 버전, GPU·드라이버, model revision, 어댑터 가중치·config, validation 지표, 재시작할 trainer 상태를 보존한다. 원문과 생성 자유 텍스트는 실행 로그로 내보내지 않는다.

## 배포 후보 경로

HF 원본 → LoRA/QLoRA 어댑터 → 동일 revision 원본에 호환 어댑터 적용 또는 병합 → llama.cpp GGUF 변환 및 양자화 → 로컬 Ollama import → 기존 `OLLAMA_MODEL`로 API 검증. HF 어댑터 출력과 병합 전후, GGUF, 양자화 후 JSON 및 탐지 결과를 작은 동일 입력에서 비교한다. Qwen2.5 adapter 직접 적용 지원은 대상 Ollama 버전에서 확인한 뒤 채택한다. 기존 `LocalVerdict` 계약과 정책 엔진을 사용한다. [Ollama import](https://docs.ollama.com/import)

## Phase 4 비교 평가

| 비교군 | 동일 조건에서 바뀌는 요소 |
|---|---|
| A. Rule Only | 정규식 기준선 |
| B. 기존 Hybrid | 정규식과 고정 artifact의 경량 ML |
| C. 범용 Qwen Only | 모든 평가 입력을 일반 Qwen 가중치로 분류 |
| D. Fine-tuned Qwen Only | C와 같은 입력·프롬프트·스키마·배포 설정에서 가중치 교체 |
| E. 범용 Qwen Adaptive Hybrid | B에 고정 버전 라우터 및 C 모델 연결 |
| F. Fine-tuned Qwen Adaptive Hybrid | E의 라우터를 고정하고 D 모델 연결 |

독립 Holdout과 기존 진단·내부 회귀셋을 각각 같은 레이블과 입력으로 실행한다. C↔D, E↔F로 모델 교체 효과를 비교한다. 별도로 E·F 각각의 기존 라우터/후보 라우터와 동일 호출 예산을 비교하고, 동일하게 라우팅된 행의 탐지 성능과 전체 성능을 함께 낸다. 양자화 영향을 분리할 때는 같은 가중치·런타임에서 정밀도만 바꾼다.

- PII와 Injection별 TP/FP/FN/TN, Precision/Recall/F1, FPR/FNR을 계산한다. 양성 전용 집합에서 음성 분모가 필요한 지표를 N/A로 표시한다. 언어, 난독화, 동시 양성, 정상 인용 및 업무 코호트로도 보고하고 분모를 표시한다.
- JSON Schema 준수율은 중복 키·추가 필드·누락·enum·잘린 답을 포함한다. 전송 실패율, 실제 추론 시도 중 유효 verdict 비율, 전체 처리 대상 중 유효 verdict 비율의 분모를 명시한다. 실패 건은 음성으로 대체하지 않고 채점 범위와 별도로 보고한다.
- 정상 요청 차단율은 **정책과 송신 가드** 기준으로, 탐지 FPR은 **레이블별 예측** 기준으로 계산한다. 송신 준비 잔존율은 합성 PII 양성 중 원문 값이 하나라도 남은 비율이다. 차단으로 송신 대상이 줄어드는 효과를 확인할 수 있도록 정상 차단율·마스킹 성공률과 함께 본다.
- 워밍업과 콜드 스타트를 구분해 프록시 입력 경로 평균/p95, 추론 호출률, 실패 사유, VRAM/RAM 피크를 기록한다. 전체 API의 응답 지연을 재는 경우 Provider·Validator·로그 I/O 포함 여부를 표시한다. 생성 API 없이 송신 준비만 검사한 실험은 실제 전송으로 표현하지 않는다.
