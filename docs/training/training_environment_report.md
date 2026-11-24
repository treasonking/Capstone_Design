# 학습 환경 검증

점검일은 2026-11-24다. Windows 호스트에서 GPU와 기존 런타임을 조회하고 WSL2 Ubuntu를 일시 구동해 GPU 인식 여부를 확인했다.

| 확인 항목 | 관측 결과 |
|---|---|
| OS / CPU / RAM | Windows 10 Pro 19045 / Intel Core i7-6700 @ 3.40 GHz / RAM 16 GiB(8 GiB 2개) |
| GPU / 드라이버 | GTX 1660 Ti, 6,144 MiB, compute capability 7.5, WDDM, NVIDIA 621.01. 점검 표본에서 3,216 MiB 여유. |
| CUDA | `nvidia-smi`가 CUDA UMD 13.5를 표시했다. 드라이버 정보이며 Toolkit이나 PyTorch wheel의 CUDA 버전을 의미하지 않는다. `nvcc`는 PATH에서 확인되지 않았다. |
| Python / 운영 가상환경 | Windows Python 3.10.10, 3.12.10. 프로젝트 `.venv`는 3.12 계열이며 scikit-learn 1.7.2를 사용한다. 이 환경과 시스템 Python 3.12의 `pip show`에서 학습용 패키지 다섯 개를 찾지 못했다. |
| 기존 Windows Python 3.10 | PyTorch 2.12.0+cpu, `torch.version.cuda=None`, `torch.cuda.is_available()=False`. Transformers 5.8.1 import 확인. PEFT, TRL, bitsandbytes는 `pip show`에서 미확인. |
| 분리 Windows 학습 환경 | Python 3.12.10, PyTorch 2.9.1+cu126, Transformers 4.57.6, PEFT 0.17.1, TRL 0.23.1, bitsandbytes 0.48.2. `pip check`, 다섯 패키지 import, `SFTConfig` 및 `SFTTrainer` import 통과. |
| WSL2 | 기존 Ubuntu 배포판은 WSL2이며 Python 3.12.3과 `/usr/lib/wsl/lib/nvidia-smi`에서 같은 GPU·VRAM·드라이버를 확인했다. 시스템 Python에는 학습 모듈 다섯 개와 pip가 없고 `venv` 모듈은 있다. 목록의 별도 Ubuntu-24.04는 WSL1이다. |
| Ollama | 루프백 서버 0.40.17, `qwen2.5:1.5b` GGUF Q4_K_M, digest `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`. 추론용이며 학습에는 HF 원본 safetensors를 사용한다. |

초기 제한 셸에서 Python 가상환경의 베이스 경로와 WSL 접근이 차단되어 별도 권한으로 읽기 검증을 진행했다. 새 패키지는 저장소의 운영 `.venv`와 분리한 로컬 `.worktrees/phase1-training/venv`에 설치했다. 첫 wheel 다운로드가 지연되어 공식 CDN의 범위 응답으로 재시도했고, 설치 전에 PyTorch 공식 인덱스의 SHA-256과 일치하는지 확인했다. [PyTorch 배포 인덱스](https://download.pytorch.org/whl/cu126/torch/)

HF 원본 revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`의 `model.safetensors` SHA-256 `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`는 공식 메타데이터와 일치했다. [Qwen 원본 revision](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)

## Windows 네이티브 CUDA·QLoRA 스모크

| 확인 항목 | 실측 |
|---|---|
| Torch GPU 경로 | CUDA 12.6, `cuda.is_available()=True`, SM 7.5. 8×8 CUDA FP16 행렬곱 통과, native BF16 미지원. |
| 4-bit 커널 | bitsandbytes `Linear4bit` NF4의 forward/backward 통과 |
| Qwen 원본 로딩 | NF4 double quant·FP16 compute·SDPA로 온디바이스 로딩 성공. 로딩 직후 Torch 할당 1,118 MiB. |
| 최소 어댑터 스텝 | 길이 256, 배치 1, rank 8, `q_proj`·`v_proj`. Gradient checkpointing 활성 및 KV cache 비활성. 합성 입력에서 completion만 손실에 포함해 AdamW forward/backward 및 1회 업데이트를 확인했다. 손실 5.0094는 유한값 확인용이다. |
| 자원 표본 | CUDA 초기화 직후 가용 5,092 MiB. PyTorch 피크 할당 2,058 MiB, 피크 예약 2,438 MiB. 프로세스 피크 RAM working set 4,111 MiB. |

이 결과는 QLoRA 단일 스텝이 이 GPU와 Windows 조합에서 실행됨을 확인한다. TRL은 import를 확인했고, 단일 스텝은 Transformers·PEFT·PyTorch로 실행했다. 전체 학습 또는 TRL 학습 루프는 Phase 3 범위다.

## 학습 방식과 제약

- **Windows 네이티브 NF4 QLoRA + FP16 compute**를 우선한다. SDPA에서 시작하고 native BF16 및 공식 FlashAttention-2 CUDA 경로는 사용하지 않는다. [bitsandbytes 설치 가이드](https://huggingface.co/docs/bitsandbytes/installation) · [공식 FlashAttention 지원표](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support)
- 명목 1.5B 가중치만 계산하면 FP16 약 3 GB, 모든 가중치를 4-bit라고 가정하면 약 0.75 GB다. 실제 메모리에는 양자화 메타데이터, 비양자화 가중치, 활성값, 어댑터·옵티마이저가 포함된다. QLoRA 스모크의 합성 입력에는 패딩이 있으므로 실제 토큰 길이 256–512와 장시간 학습의 여유를 다시 측정한다.
- FP16 LoRA는 가용 VRAM이 충분할 때 별도 측정할 후보로 남긴다. WSL2는 Windows 패키지 조합이 바뀌거나 재현되지 않을 때의 대안이다. WSL2에서 GPU는 확인했고, WSL2 학습 wheel 및 전·후방 경로는 미검증이다. [NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

재현에 사용한 패키지 목록과 스모크 스크립트, 출력은 로컬 `.worktrees/phase1-training/`에 있다. 저장소의 학습 계획은 [Phase 3 후보 설정](finetuning_plan.md)에 기록했다.
