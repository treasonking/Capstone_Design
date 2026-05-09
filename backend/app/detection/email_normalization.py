from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b",
    flags=re.IGNORECASE,
)
_AT_TOKEN_PATTERN = re.compile(
    r"(?:\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|\bat\b)",
    flags=re.IGNORECASE,
)
_DOT_TOKEN_PATTERN = re.compile(
    r"(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\bdot\b)",
    flags=re.IGNORECASE,
)
_EXPLICIT_MARKER_PATTERN = re.compile(
    r"[\[\(\{]\s*(?:at|dot)\s*[\]\)\}]",
    flags=re.IGNORECASE,
)
_OBFUSCATED_EMAIL_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9._%+-])"
    rf"[A-Za-z0-9][A-Za-z0-9._%+-]{{0,63}}"
    rf"\s*{_AT_TOKEN_PATTERN.pattern}\s*"
    rf"[A-Za-z0-9-]+(?:\s*{_DOT_TOKEN_PATTERN.pattern}\s*[A-Za-z0-9-]+)+"
    rf"(?![A-Za-z0-9._%+-])",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ObfuscatedEmailMatch:
    start: int
    end: int
    raw_text: str
    normalized_email: str


def normalize_obfuscated_email_candidate(text: str) -> str:
    normalized = _AT_TOKEN_PATTERN.sub("@", text)
    normalized = _DOT_TOKEN_PATTERN.sub(".", normalized)
    return re.sub(r"\s+", "", normalized)


def _should_accept_bare_word_form(raw_text: str, normalized_email: str) -> bool:
    if _EXPLICIT_MARKER_PATTERN.search(raw_text):
        return True
    local_part, _sep, _domain = normalized_email.partition("@")
    return len(local_part) >= 3


def extract_obfuscated_emails(text: str) -> list[ObfuscatedEmailMatch]:
    matches: list[ObfuscatedEmailMatch] = []
    seen: set[tuple[int, int, str]] = set()

    for match in _OBFUSCATED_EMAIL_PATTERN.finditer(text):
        raw_text = match.group(0)
        normalized_email = normalize_obfuscated_email_candidate(raw_text)
        if EMAIL_PATTERN.fullmatch(normalized_email) is None:
            continue
        if not _should_accept_bare_word_form(raw_text, normalized_email):
            continue

        key = (match.start(), match.end(), normalized_email.lower())
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            ObfuscatedEmailMatch(
                start=match.start(),
                end=match.end(),
                raw_text=raw_text,
                normalized_email=normalized_email,
            )
        )

    return matches


def restore_obfuscated_emails(text: str) -> tuple[str, list[str]]:
    matches = extract_obfuscated_emails(text)
    if not matches:
        return text, []

    parts: list[str] = []
    restored_emails: list[str] = []
    cursor = 0

    for match in matches:
        parts.append(text[cursor:match.start])
        parts.append(match.normalized_email)
        restored_emails.append(match.normalized_email)
        cursor = match.end

    parts.append(text[cursor:])
    return "".join(parts), restored_emails
