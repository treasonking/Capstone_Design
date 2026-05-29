# PAPILLON Comparison for Privacy-Preserving LLM Use

## Reference

- Title: PAPILLON: Privacy Preservation from Internet-based and Local Language Model Ensembles
- Paper: https://arxiv.org/abs/2410.17127
- PDF: https://arxiv.org/pdf/2410.17127
- Code: https://github.com/siyan-sylvia-li/PAPILLON

## Why PAPILLON is selected

본 프로젝트의 핵심 목적은 공공기관·사내망 환경에서 직원이 LLM을 사용할 때 개인정보가 외부 LLM 또는 내부 LLM으로 원문 그대로 전달되는 위험을 줄이는 것이다. PAPILLON은 사용자가 외부/proprietary LLM에 민감정보가 포함된 질의를 전달할 때 발생하는 privacy leakage 문제를 다루므로, 본 프로젝트의 PII 유출 방지 목적과 직접적으로 연결된다.

기존 비교 대상으로 검토했던 PIGuard는 Prompt Injection guardrail의 over-defense 문제를 다루므로, 본 프로젝트에서 확인된 rule-driven false positive 문제와 연결될 수 있다. 그러나 PIGuard는 개인정보 유출 방지 프록시라는 본 프로젝트의 전체 목적과는 비교 범위가 좁다. 따라서 PIGuard는 관련 연구로 유지하고, 메인 비교 논문은 PAPILLON으로 교체한다.

## Comparison Table

| 항목 | Capstone LLM Security Proxy | PAPILLON |
|---|---|---|
| Target environment | Public-sector and internal network LLM use | Internet-based and local LLM ensemble use |
| Main risk | PII leakage through employee prompts and unsafe LLM usage | Privacy leakage when sensitive user queries are sent to proprietary LLMs |
| Main protection mechanism | Proxy-side detection, masking, blocking, output validation, audit logging | Privacy-conscious delegation between local and external LLMs |
| Sensitive data handling | Regex/rule/model-based PII detection and masking | Query transformation/delegation to reduce leakage |
| External LLM usage | Requests are inspected before being sent to external or internal LLMs | External LLM is used selectively through a privacy-preserving pipeline |
| Prompt Injection | Included as one detection target | Not the primary focus |
| Audit log | Minimal raw-free audit metadata and integrity extension | Not the primary focus |
| Evaluation focus | PII detection, injection detection, policy action, latency | Privacy leakage and response quality |
| Direct metric comparability | Partial | Partial |

## Common ground

두 연구는 모두 외부 LLM의 성능을 활용하면서도 사용자의 민감정보가 외부로 과도하게 노출되는 문제를 줄이려 한다. 본 프로젝트는 프록시 기반 정책 집행 구조이고, PAPILLON은 로컬 모델과 외부 모델의 delegation pipeline이라는 차이가 있지만, 개인정보가 포함된 LLM 입력을 안전하게 처리하려는 목적은 유사하다.

## Difference

PAPILLON은 privacy-preserving delegation에 초점을 두며, 본 프로젝트는 공공기관·사내망 업무 시나리오에서 프록시가 개인정보 탐지, 마스킹, 차단, Prompt Injection 탐지, 출력 재검사, 감사로그를 수행하는 운영형 보안 구조에 초점을 둔다.

따라서 본 프로젝트와 PAPILLON의 비교는 개인정보 유출 방지와 privacy-utility trade-off 관점에서 수행하며, Prompt Injection 탐지 성능 비교는 별도 실험으로 분리한다.

## Reporting boundary

본 프로젝트는 PAPILLON의 성능 수치를 그대로 재현했다고 주장하지 않는다. PAPILLON은 목적과 구조 비교의 기준 연구로 사용한다. PAPILLON 코드를 실제 실행하여 동일 데이터셋 또는 변환 데이터셋에서 실험한 경우에만 정량 비교 결과를 표기한다.

## Paper-ready sentence

PAPILLON은 외부 또는 proprietary LLM에 민감정보가 포함된 사용자 질의가 전달될 때 발생하는 privacy leakage 문제를 다루며, 로컬 모델과 외부 모델을 조합하여 privacy와 response quality 사이의 균형을 맞추는 pipeline을 제안한다. 이는 본 연구가 공공기관·사내망 환경에서 직원의 LLM 입력을 프록시가 사전 검사하고 개인정보를 마스킹 또는 차단하는 목적과 직접적으로 연결된다. 다만 PAPILLON은 Prompt Injection 탐지보다는 privacy-preserving delegation에 초점을 두므로, 본 연구와의 비교는 개인정보 유출 방지 및 privacy-utility trade-off 관점으로 제한한다.
