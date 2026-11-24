# Phase 1 탐지 실패 분석

기준 커밋은 `b31c8475c59019e8bbf9e5d9f6dc485b4f50740f`다. README의 2026-11-19 적응형 평가 섹션은 아래 기존 수치와 같은 코호트를 설명한다. README의 external-tuned 표는 별도 학습 artifact와 평가 분할을 사용한다. [기존 Markdown 평가표](../../reports/ollama_adaptive_results.md) · [기존 JSON 결과](../../reports/ollama_adaptive_results.json)

## 기존 결과

| 코호트와 지표 | 기존 Hybrid → Adaptive Hybrid |
|---|---|
| 내부 PII F1 / Injection F1 | 각각 0.988 / 1.000, 두 모드 동일 |
| deepset 부분집합 F1 | 0.087 → 0.128 |
| Lakera 양성 부분집합 Recall | 0.480 → 0.510 |
| ProtectAI 부분집합 Recall | 0.000 → 0.000 |
| 전체 Adaptive 추론 호출 | 70/458 |
| 합성 양성의 PII 송신 준비 잔존 | 2/5 → 0/5 |
| 내부 PII 코호트 차단 | 8/70 → 29/70 |

내부·합성 수치는 회귀용이고 외부 수치는 각각 100건의 고정된 부분집합에 한정된다. Lakera는 양성만 있어 FPR을 계산할 수 없다. 합성 송신 평가는 메모리에서 송신 직전 값을 확인하며 upstream에 전송하지 않는다.

## 2026-11-24 실제 Ollama 재실행

동일한 458건을 네 모드로 비교했다. 데이터와 경량 artifact의 SHA-256, 탐지 설정과 Ollama 설정은 기존 JSON과 일치했다. Q4_K_M 모델 digest도 기존 실행 환경 문서와 일치했다. Ollama 서버 버전은 기존 0.40.16, 이번 0.40.17이다.

| 비교 항목 | 재실행 결과 |
|---|---|
| Adaptive Hybrid 탐지 | 위 표의 탐지 지표와 70/458회 추가 검사 호출을 재현했다. ProtectAI는 0/100회 호출이었다. |
| 내부 PII 차단·합성 송신 | 8/70 → 29/70 및 2/5 → 0/5를 각각 재현했다. |
| Ollama Only 인젝션 | deepset TP 9→6, F1 0.340→0.240. Lakera TP 6→5, Recall 0.060→0.050. ProtectAI TP 4/50 및 내부 TP 2/54는 동일했다. |
| Adaptive Hybrid 정책 차단 | Lakera에서 기존 75/100, 이번 74/100. Lakera의 인젝션 탐지 혼동행렬은 같았다. |
| 응답 계약 | 이번 Ollama Only 458건과 Adaptive Hybrid 호출 70건에서 모두 유효한 verdict를 받았다. |

비교에서 위 세 항목(deepset 및 Lakera 단독 탐지와 Lakera 적응형 차단)이 달랐다. 서버 버전이 달랐지만 버전만 바꾼 대조 실험은 없었다. 지연은 시스템 부하가 달랐고, 전체 프록시 API의 지연으로 비교하지 않았다. 아래 원인별 진단은 별도 실행한 집계다.

## ProtectAI 라우팅 실패

[진단 모듈](../../evaluation/adaptive_failure_diagnostics.py)은 기존 `_inputs`, 경량 artifact, 정책과 적응형 preview 경로를 사용한다. Phase 1 재계산에서 기본 artifact가 활성화됐고 데이터·artifact SHA-256이 기존 결과와 일치했다.

| 레이블 | 건수 | 인젝션 클래스 점수 최소 / 중앙 / 최대 | 0.6 미만 | 최상위 레이블 Injection / Safe |
|---|---:|---|---:|---:|
| 음성 | 50 | 0.331 / 0.4325 / 0.583 | 50 | 41 / 9 |
| 양성 | 50 | 0.341 / 0.444 / 0.555 | 50 | 46 / 4 |

두 분포가 크게 겹친다. `prompt_injection_score`는 인젝션 클래스 점수이고, 라우터는 **최상위로 예측된 위험 유형의 confidence**가 0.7±0.1인지 확인한다. 최상위가 Safe인 경우 이 구간 검사 대상에서 제외한다. 양성 50건 모두 정규식 인젝션 신호와 경량 모델의 채택된 인젝션 신호가 없었다. 양성·음성 모두 문맥·정규화 PII, 의심스러운 표현 패턴 등 다른 라우팅 분기가 작동하지 않아 100/100건 `clear_baseline`이었다. [ProtectAI 부분집합](../../reports/baselines/multi_dataset/protectai_shared_eval.csv)의 헤더 제외 1·3·5번째 행이 동시 미탐 검토 예다.

이 코호트에서 `clear_baseline`은 추가 검사를 촉발하는 근거가 없었다는 상태다. 양성과 음성 점수의 겹침을 감안하면 단순 하한 하향이 탐지 이득과 호출 비용을 개선할지 확정할 수 없다. 후속 검증은 낮은 점수 구간의 표본 검사와 동일 호출 예산으로 양성 포착률·정상 호출률을 같이 비교한다.

## 범용 Qwen 단독 탐지와 출력 계약

기존 Ollama Only에서 내부 PII 양성 40건을 모두 찾았으나 정상 30건도 모두 PII로 분류했다. 내부 인젝션은 양성 54건 중 2건을 검출했다. 외부 양성의 단독 모델 TP는 deepset 9/44, ProtectAI 4/50, Lakera 6/100이다.

`ollama_detector.py`는 정규화한 입력을 JSON 문자열 필드로 감싸고, 고정 system prompt와 온도 0, `num_ctx=8192`, `num_predict=256`으로 분류한다. 서버에 JSON Schema를 요청하고 클라이언트에서도 중복 키·필드·enum·응답 완료 상태를 확인한다. 기존 실행은 유효 verdict 458/458건이어서, 높은 오탐·미탐은 이 설정에서 의미 분류 오류로 관찰됐다. 생성 스키마 강제는 정확한 정답을 보장하지 않는다.

### 프롬프트와 언어 표본 대조

내부 평가에서 작업·정답·한글 포함 여부별로 처음 두 건씩 총 14건을 선택했다. 한글 미포함 PII 양성은 해당 코호트에 없었다. 동일 모델·설정·JSON Schema로 기존 지침과 값 없는 언급·인용·실제 지시를 더 명시한 지침을 비교했다. 28/28회 모두 유효한 verdict였다.

| 작업과 레이블 | 한글 포함 | 한글 미포함 |
|---|---|---|
| PII 음성 | 두 프롬프트 모두 2/2를 `OBFUSCATED_PII`로 오분류 | 두 프롬프트 모두 2/2를 `OBFUSCATED_PII`로 오분류 |
| PII 양성 | 기존 2/2, 지침 보강 후 1/2 탐지 | 표본 없음 |
| 인젝션 양성 | 두 프롬프트 모두 0/2 탐지, 전부 `CLEAR` | 두 프롬프트 모두 0/2 탐지, 전부 `CLEAR` |
| 인젝션 음성 | 두 프롬프트 모두 2/2 `CLEAR` | 두 프롬프트 모두 2/2 `CLEAR` |

이 표본은 두 오류가 양쪽 문자 그룹에서 발생하고, 점검한 지침 보강으로 해소되지 않았음을 보여준다. 관측된 오류는 유효한 enum 선택에서 발생했다. 한글 포함 여부는 언어의 대리 지표이고, 표본 수와 양성 분포로는 한국어·영어 성능 차이를 추정하기 어렵다. 프롬프트 전반의 영향과 구분되는 모델 고유 한계는 HF 원본·Q4_K_M의 정밀도 및 동일 런타임 대조를 추가하기 전까지 미확정이다.

## 정책 차단과 탐지 FPR

`adaptive_detector.py`는 기존 정책으로 이미 차단한 요청을 건너뛴다. 라우팅 이후 PII 양성 verdict 또는 문맥·정규화 PII 라우팅은 신뢰 가능한 원문 위치가 없어 `PII_UNMASKABLE_DETECTED` 신호를 추가한다. 그 경우 기존에 마스킹 가능한 값이 있어도 같은 요청의 나머지 잠재 PII에 대해 차단할 수 있다. Ollama 실패는 `LOCAL_LLM_REVIEW_FAILED`로 차단하고, 의미상 탐지 결과와 분리한다. 인젝션 양성은 별도 `INJ_LOCAL_LLM_DETECTED` 신호다. 마지막으로 송신 가드가 마스킹/정책 결과를 확인한다. [기본 정책](../../policies/policy.yaml)

기존 내부 PII 탐지 FPR은 두 모드 모두 1/30으로 같았다. 8→29는 양성과 음성이 섞인 코호트 전체의 송신 준비 차단 건수다. 정상 요청 차단율의 분모는 정상 30건이고, 양성 차단 건수나 정책 실패 차단을 FPR에 더하지 않는다. 로컬 신호는 검출 위치를 제공하지 않으므로 더 많이 차단하는 설정이 마스킹 가용성을 낮출 수 있다.

| 내부 PII 정책 진단 | 관측 건수 |
|---|---:|
| 정답 양성 중 두 모드 모두 정책 차단 | 8/40 |
| 정답 양성 중 Hybrid 송신 준비 → Adaptive 정책 차단 | 21/40 |
| 정답 양성 중 두 모드 모두 송신 준비 | 11/40 |
| 정답 음성 중 차단 | Hybrid 0/30, Adaptive 0/30 |
| 추가 차단 중 Ollama 검사 실패 / 송신 가드 자체 차단 | 각각 0/21 |

추가 차단 21건은 전부 임계치 근접으로 라우팅됐고, Ollama가 위치 없는 PII 양성을 반환해 정책에서 `PII_UNMASKABLE_DETECTED`로 차단했다. 21건 모두 기존 정규식 PII 신호가 있었으며 문맥·정규화 PII 분기가 직접 추가한 차단은 0건이었다. 기존 마스킹 가능한 신호에 위치 없는 양성 신호가 추가된 결과다. PII가 포함된 요청이라는 정답과 차단 시 기존 마스킹으로 충분했는지는 별개다. 위치 검증과 합성 송신 잔존이 포함된 평가에서 차단의 추가 이득을 측정해야 한다.

## 재현 명령

```powershell
python -m evaluation.adaptive_compare --warmup
python -m evaluation.adaptive_compare --output ../phase1-adaptive-reproduction
python -m evaluation.adaptive_failure_diagnostics --compare-prompts
```

실제 Ollama 서버는 루프백의 로컬 모델로 사용한다. 워밍업은 콜드 스타트 시 해당 명령에만 타임아웃을 늘리고, 비교는 기존 15초 설정으로 복구한다. 진단은 점수·집계·벤치마크 행 번호만 출력한다.
