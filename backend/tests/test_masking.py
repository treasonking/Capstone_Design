from backend.app.detection.models import DetectionResult
from backend.app.detection.reason_codes import ReasonCode
from backend.app.engine.masking import apply_masking


def test_apply_masking_for_email_and_phone() -> None:
    text = "문의: abcd@gmail.com / 010-1234-5678"
    detections = [
        DetectionResult(
            detector="PII_REGEX",
            category="EMAIL",
            label="email",
            confidence=0.95,
            reason_code=ReasonCode.PII_EMAIL_DETECTED.value,
            start=text.index("abcd@gmail.com"),
            end=text.index("abcd@gmail.com") + len("abcd@gmail.com"),
            matched_text="abcd@gmail.com",
        ),
        DetectionResult(
            detector="PII_REGEX",
            category="PHONE",
            label="phone",
            confidence=0.9,
            reason_code=ReasonCode.PII_PHONE_DETECTED.value,
            start=text.index("010-1234-5678"),
            end=text.index("010-1234-5678") + len("010-1234-5678"),
            matched_text="010-1234-5678",
        ),
    ]

    masked = apply_masking(text, detections)
    assert "ab***@gmail.com" in masked
    assert "010-12**-****" in masked


def test_apply_masking_for_country_code_phone() -> None:
    text = "국가코드 번호는 +82 10 1234 5678 입니다."
    raw = "+82 10 1234 5678"
    detections = [
        DetectionResult(
            detector="PII_REGEX",
            category="PHONE",
            label="phone",
            confidence=0.9,
            reason_code=ReasonCode.PII_PHONE_DETECTED.value,
            start=text.index(raw),
            end=text.index(raw) + len(raw),
            matched_text=raw,
        )
    ]

    masked = apply_masking(text, detections)
    assert "010-12**-****" in masked


def test_apply_masking_for_address() -> None:
    text = "주소는 대전광역시 동구 대학로 62 입니다."
    raw = "대전광역시 동구 대학로 62"
    detections = [
        DetectionResult(
            detector="PII_REGEX",
            category="ADDRESS",
            label="address",
            confidence=0.88,
            reason_code=ReasonCode.PII_ADDRESS_DETECTED.value,
            start=text.index(raw),
            end=text.index(raw) + len(raw),
            matched_text=raw,
        )
    ]

    masked = apply_masking(text, detections)
    assert "대전광역시 동구 대학로 **" in masked
