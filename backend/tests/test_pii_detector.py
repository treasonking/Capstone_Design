from backend.app.detection.pii_detector import detect_pii
from backend.app.detection.reason_codes import ReasonCode


def test_detect_pii_multiple_categories() -> None:
    text = "연락처 010-1234-5678, 이메일 test.user@example.com, 주민번호 900101-1234567"
    results = detect_pii(text)
    reason_codes = {item.reason_code for item in results}

    assert ReasonCode.PII_PHONE_DETECTED.value in reason_codes
    assert ReasonCode.PII_EMAIL_DETECTED.value in reason_codes
    assert ReasonCode.PII_RRN_DETECTED.value in reason_codes


def test_detect_pii_safe_text() -> None:
    assert detect_pii("오늘은 보안 정책 회의가 있습니다.") == []

