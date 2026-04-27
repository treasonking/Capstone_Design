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


def test_detect_pii_phone_variants() -> None:
    text = "연락처는 +82 10 1234 5678 또는 01012345678 입니다."
    results = detect_pii(text)
    phones = [item for item in results if item.reason_code == ReasonCode.PII_PHONE_DETECTED.value]
    assert len(phones) >= 2


def test_detect_pii_rrn_space_variant() -> None:
    text = "주민번호 형식 테스트: 900101 1234567"
    results = detect_pii(text)
    assert any(item.reason_code == ReasonCode.PII_RRN_DETECTED.value for item in results)


def test_version_number_not_detected_as_account() -> None:
    text = "버전은 01.10.2026으로 업데이트되었습니다."
    results = detect_pii(text)
    reason_codes = {item.reason_code for item in results}

    assert ReasonCode.PII_ACCOUNT_DETECTED.value not in reason_codes
    assert ReasonCode.PII_PHONE_DETECTED.value not in reason_codes


def test_math_expression_not_detected_as_account() -> None:
    text = "1234-5678-90을 계산식 예제로 사용했다."
    results = detect_pii(text)
    reason_codes = {item.reason_code for item in results}

    assert ReasonCode.PII_ACCOUNT_DETECTED.value not in reason_codes


def test_approval_number_not_detected_as_account() -> None:
    text = "승인번호 1234-5678-90을 확인해주세요."
    results = detect_pii(text)
    reason_codes = {item.reason_code for item in results}

    assert ReasonCode.PII_ACCOUNT_DETECTED.value not in reason_codes


def test_account_with_bank_context_detected() -> None:
    text = "입금 계좌는 국민은행 123456-78-901234입니다."
    results = detect_pii(text)
    reason_codes = {item.reason_code for item in results}

    assert ReasonCode.PII_ACCOUNT_DETECTED.value in reason_codes


def test_korean_international_phone_with_parentheses_detected() -> None:
    cases = [
        "+82 (10) 2222 3333",
        "+82 (10) 2222-3333",
        "+82-(10)-2222-3333",
        "+82 10 2222 3333",
        "0082 (10) 2222 3333",
        "+82 (010) 2222 3333",
    ]

    for text in cases:
        results = detect_pii(text)
        reason_codes = {item.reason_code for item in results}
        assert ReasonCode.PII_PHONE_DETECTED.value in reason_codes


def test_korean_international_phone_false_positive_guards() -> None:
    cases = [
        "+82 version 10.2222.3333",
        "+82 (10) 2026 release",
        "+82 (10) is country and area explanation",
    ]

    for text in cases:
        results = detect_pii(text)
        reason_codes = {item.reason_code for item in results}
        assert ReasonCode.PII_PHONE_DETECTED.value not in reason_codes
