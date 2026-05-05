# Hybrid Detection Architecture

## Goal

정규표현식, 정책 룰, 경량 문장 분류 모델을 결합한 하이브리드 LLM 보안 프록시를 통해 공공기관 및 사내망 환경에서 생성형 AI 사용 시 개인정보 유출과 프롬프트 인젝션 위험을 줄인다.

## Flow

```text
User Input
  ↓
Frontend UI
  ↓
LLM Security Proxy
  ↓
1차 탐지: Regex 기반 PII Detector
  ↓
2차 탐지: Rule 기반 Prompt Injection Detector
  ↓
3차 탐지: Lightweight Model 기반 Context Classifier
  ↓
Policy Engine
  ↓
ALLOW / MASK / BLOCK / WARN
  ↓
Mock LLM or Local/Remote LLM
  ↓
Output Inspection
  ↓
User Response + Audit Log
```

## Component Mapping

| Layer | Purpose | Main Files |
|---|---|---|
| Frontend UI | 사용자 입력, 정책 선택, 차단/마스킹 사유 표시 | `frontend/demo.html`, `frontend/src/constants/reasonMessages.ts` |
| Regex PII Detector | 주민번호, 전화번호, 이메일, 카드번호, 주소 등 구조화된 PII 1차 탐지 | `backend/app/detection/pii_detector.py` |
| Rule Injection Detector | 정책 무시, 시스템 프롬프트 탈취, 역할 탈옥, 원문 유출 요청 탐지 | `backend/app/detection/injection_detector.py` |
| Lightweight Classifier | 정규식/룰만으로 애매한 문맥형 위험을 보조 분류 | `backend/app/models/lightweight_classifier.py`, `training/train_lightweight_classifier.py` |
| Policy Engine | 여러 탐지 결과를 종합해 `ALLOW/WARN/MASK/BLOCK` 결정 | `backend/app/engine/policy_engine.py`, `policies/default_policy.yaml`, `policies/strict.yaml` |
| Proxy Service | 입력/출력 양방향 검사, upstream LLM 호출, audit summary 구성 | `backend/app/services/proxy_service.py`, `backend/app/api/proxy.py` |
| Audit Log | 원문 미저장 원칙 아래 request metadata만 저장 | `backend/app/services/audit_service.py` |

## Detection Result Schema

모든 탐지기는 공통 `DetectionResult` 스키마를 사용한다.

```python
@dataclass
class DetectionResult:
    detector: str
    category: str
    label: str
    confidence: float
    start: int | None = None
    end: int | None = None
    matched_text: str | None = None
    masked_text: str | None = None
    reason_code: str = "UNKNOWN"
    severity: str = "LOW"
    source: str = "regex"  # regex | rule | model
```

## Why Hybrid

| Method | Strength | Limitation | Role in Final System |
|---|---|---|---|
| Regex | 빠르고 설명 가능하며 구조화된 개인정보 탐지에 강함 | 우회 표현과 문맥형 위험에는 약함 | 1차 방어선 |
| Rule | 명확한 공격 문장을 안정적으로 차단 | 표현 변형이 심한 경우 누락 가능 | 2차 방어선 |
| Lightweight Model | 문맥형 위험, 애매한 경계 사례를 보조 분류 | 단독 사용 시 오탐/미탐 가능성 | 보조 신호 |
| Policy Engine | 조직 정책에 맞게 일관된 action 결정 | 정책 설계 품질에 의존 | 최종 결정 계층 |

## Public-Sector Design Notes

- 관리자 화면은 원문 prompt/response를 직접 보여주지 않는다.
- 감사 로그에는 `request_id`, `reason_code`, `detector_counts`, `latency_ms`, `policy_version`, `masked_preview`만 저장한다.
- `strict` 정책은 시연/관리자 검토용이고, `default` 정책은 실사용 친화적인 `WARN/MASK/BLOCK` 균형을 의도한다.
