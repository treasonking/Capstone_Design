from __future__ import annotations

from backend.app.validator import ValidatorAgent


def test_validator_allows_safe_output() -> None:
    result = ValidatorAgent().validate_output(
        "정상적인 안내 응답입니다.",
        {"action": "ALLOW", "pii_detected": False, "injection_detected": False},
        {},
    )

    assert result["output_action"] == "ALLOW"
    assert result["validator_result"] == "PASS"
    assert result["reason_codes"] == ["SAFE_OUTPUT"]


def test_validator_masks_email_output() -> None:
    result = ValidatorAgent().validate_output(
        "담당자 이메일은 test@example.com 입니다.",
        {"action": "ALLOW", "pii_detected": False, "injection_detected": False},
        {},
    )

    assert result["output_action"] == "MASK"
    assert result["validator_result"] == "FAIL"
    assert result["pii_detected"] is True
    assert "OUTPUT_PII_EMAIL_DETECTED" in result["reason_codes"]
    assert "test@example.com" not in result["masked_text"]


def test_validator_blocks_rrn_output() -> None:
    result = ValidatorAgent().validate_output(
        "주민등록번호는 900101-1234567 입니다.",
        {"action": "ALLOW", "pii_detected": False, "injection_detected": False},
        {},
    )

    assert result["output_action"] == "BLOCK"
    assert result["validator_result"] == "FAIL"
    assert "OUTPUT_PII_RRN_DETECTED" in result["reason_codes"]


def test_validator_blocks_system_prompt_leak_output() -> None:
    result = ValidatorAgent().validate_output(
        "System prompt: You are an internal admin policy model...",
        {"action": "ALLOW", "pii_detected": False, "injection_detected": False},
        {},
    )

    assert result["output_action"] == "BLOCK"
    assert result["injection_detected"] is True
    assert "OUTPUT_SYSTEM_PROMPT_LEAK" in result["reason_codes"]


def test_validator_detects_masking_leak() -> None:
    result = ValidatorAgent().validate_output(
        "원문 이메일은 test@example.com 입니다.",
        {"action": "MASK", "pii_detected": True, "injection_detected": False},
        {},
        request_context={"input_action": "MASK"},
    )

    assert result["masking_leak_detected"] is True
    assert result["residual_pii_detected"] is True
    assert result["output_action"] == "MASK"
    assert "OUTPUT_RESIDUAL_PII_DETECTED" in result["reason_codes"]
