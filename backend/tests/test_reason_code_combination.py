from backend.app.services.proxy_service import _combine_reason_codes


def test_combine_reason_codes_drops_safe_input_when_non_safe_exists() -> None:
    result = _combine_reason_codes(["PII_EMAIL_OBFUSCATED"], ["SAFE_INPUT"])

    assert result == ["PII_EMAIL_OBFUSCATED"]


def test_combine_reason_codes_keeps_output_non_safe_reason() -> None:
    result = _combine_reason_codes(["SAFE_INPUT"], ["PII_EMAIL_DETECTED"])

    assert result == ["PII_EMAIL_DETECTED"]


def test_combine_reason_codes_returns_safe_input_when_both_are_safe() -> None:
    result = _combine_reason_codes(["SAFE_INPUT"], ["SAFE_INPUT"])

    assert result == ["SAFE_INPUT"]


def test_combine_reason_codes_returns_safe_input_when_empty() -> None:
    result = _combine_reason_codes([], [])

    assert result == ["SAFE_INPUT"]


def test_combine_reason_codes_keeps_non_safe_reason_when_mixed() -> None:
    result = _combine_reason_codes(["INJ_POLICY_BYPASS"], ["SAFE_INPUT"])

    assert result == ["INJ_POLICY_BYPASS"]


def test_combine_reason_codes_respects_ordered_reason_priority() -> None:
    result = _combine_reason_codes(
        ["PII_EMAIL_OBFUSCATED"],
        ["PII_EMAIL_DETECTED"],
    )

    assert result == ["PII_EMAIL_OBFUSCATED", "PII_EMAIL_DETECTED"]
