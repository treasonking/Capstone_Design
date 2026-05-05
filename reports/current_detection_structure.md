# Current Detection Structure

## 1. Initial Repository Classification

- Initial classification before this hybrid refactor: **C. Regex + Rule Engine**
- Why:
  - `backend/app/detection/pii_detector.py` already handled structured PII with regex.
  - `backend/app/detection/injection_detector.py` already handled prompt injection with keyword/rule logic.
  - `backend/app/engine/policy_engine.py` already mapped detections to `ALLOW/WARN/MASK/BLOCK`.
  - There was no lightweight text classifier connected to the proxy path yet.

## 2. Current PII Detection

- Current method: Regex-based first-line defense
- Files:
  - `backend/app/detection/pii_detector.py`
  - `backend/app/engine/masking.py`
- Supported types:
  - resident registration number
  - mobile phone
  - landline phone
  - email
  - account number candidate
  - card number candidate
  - IP address
  - address
  - name candidate

## 3. Current Prompt Injection Detection

- Current method: Rule-based prompt injection detector
- Files:
  - `backend/app/detection/injection_detector.py`
- Covered categories:
  - direct override
  - system prompt leak
  - rule disclosure
  - role-play bypass
  - policy bypass
  - debug/admin mode switching
  - multi-step extraction
  - obfuscated injection
  - data exfiltration

## 4. Detection Result Integration

- Common schema:
  - `backend/app/detection/types.py`
  - `backend/app/detectors/types.py`
- Proxy integration:
  - `backend/app/services/proxy_service.py`
- Policy integration:
  - `backend/app/engine/policy_engine.py`
- Response fields preserved:
  - `action`
  - `reason_code`
  - `reasons`
  - `input_action`
  - `output_action`
  - `audit_summary`

## 5. Lightweight Model Integration

- Current method: TF-IDF + Logistic Regression auxiliary classifier
- Files:
  - `backend/app/models/lightweight_classifier.py`
  - `backend/app/models/model_config.py`
  - `training/train_lightweight_classifier.py`
- Runtime behavior:
  - model files exist -> auxiliary model signal enabled
  - model files missing -> proxy stays alive and model detector is disabled

## 6. Final Classification After This Task

- Current classification after the requested implementation: **D. Regex + Rule + Lightweight Model**

## 7. Limitation

- Regex PII detection is still strongest on structured values.
- Rule-based injection detection can still miss highly novel paraphrases.
- Lightweight model is intentionally auxiliary and should not override strong regex/rule decisions by itself.
