from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.app.detection.models import DetectionResult
from backend.app.detection.pii_detector import detect_pii
from backend.app.engine.masking import apply_masking


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = PROJECT_ROOT / "reports" / "scanner_result.json"
DEFAULT_EXCLUDED_PATHS = {
    PROJECT_ROOT / "reports" / "evaluation_report.md",
}
SUPPORTED_SUFFIXES = {".log", ".txt", ".json", ".jsonl", ".csv"}
TEXTUAL_CSV_HINTS = ("prompt", "message", "content", "text", "body", "input", "output", "error", "exception")


def _default_targets(include_reports: bool) -> list[Path]:
    targets = [
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "proxy.db",
        PROJECT_ROOT / "performance",
    ]
    if include_reports:
        targets.append(PROJECT_ROOT / "reports")
    return targets


def _iter_candidate_files(include_reports: bool) -> list[Path]:
    files: list[Path] = []
    for target in _default_targets(include_reports):
        if not target.exists():
            continue
        if target.is_file():
            if target.name == "proxy.db" or target.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(target)
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() in DEFAULT_EXCLUDED_PATHS:
                continue
            if path.name == "proxy.db" or path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(path)
    return sorted({path.resolve() for path in files})


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        return _read_csv_text(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _looks_numeric(value: str) -> bool:
    stripped = value.strip()
    if not stripped or stripped.upper() == "N/A":
        return True
    allowed = set("0123456789+-.:%")
    return all(char in allowed for char in stripped)


def _skip_locust_summary_row(row: dict[str, str]) -> bool:
    row_type = str(row.get("Type", "") or "").strip()
    row_name = str(row.get("Name", "") or "").strip().lower()
    if row_name == "aggregated":
        return True
    if row_type.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"} and row_name.startswith("/"):
        return True
    return False


def _read_csv_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return file.read()

        fieldnames = [field or "" for field in reader.fieldnames]
        preferred_fields = [
            field for field in fieldnames if any(hint in field.lower() for hint in TEXTUAL_CSV_HINTS)
        ]

        chunks: list[str] = []
        for row in reader:
            if _skip_locust_summary_row(row):
                continue
            values: list[str] = []
            candidate_fields = preferred_fields or fieldnames
            for field in candidate_fields:
                value = str(row.get(field, "") or "").strip()
                if not value or _looks_numeric(value):
                    continue
                values.append(f"{field}: {value}")

            if values:
                chunks.append(" | ".join(values))

        return "\n".join(chunks)


def _masked_excerpt(text: str, start: int, end: int, window: int = 36) -> str:
    excerpt_start = max(0, start - window)
    excerpt_end = min(len(text), end + window)
    excerpt = text[excerpt_start:excerpt_end]
    adjusted_start = start - excerpt_start
    adjusted_end = adjusted_start + (end - start)

    detections = detect_pii(excerpt)
    if detections:
        excerpt = apply_masking(excerpt, detections)
    else:
        excerpt = excerpt[:adjusted_start] + "***" + excerpt[adjusted_end:]
    return excerpt.replace("\n", "\\n")


def _masked_match_text(detection: DetectionResult) -> str:
    normalized = DetectionResult(
        detector="PII_REGEX",
        category=detection.category,
        label=detection.label,
        confidence=detection.confidence,
        reason_code=detection.reason_code,
        start=0,
        end=len(detection.matched_text),
        matched_text=detection.matched_text,
        masked_text=None,
        severity=detection.severity,
        source=detection.source,
        metadata=dict(detection.metadata),
    )
    return apply_masking(detection.matched_text, [normalized])


def scan_files(include_reports: bool = False) -> dict[str, Any]:
    files = _iter_candidate_files(include_reports)
    findings: list[dict[str, Any]] = []
    scanned_files = 0

    for path in files:
        scanned_files += 1
        text = _read_text(path)
        detections = detect_pii(text)
        for detection in detections:
            findings.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "reason_code": detection.reason_code,
                    "category": detection.category,
                    "score": round(detection.score, 3),
                    "masked_match": _masked_match_text(detection),
                    "masked_excerpt": _masked_excerpt(text, detection.start, detection.end),
                }
            )

    summary = {
        "scanned_files": scanned_files,
        "sensitive_findings": len(findings),
        "include_reports": include_reports,
        "supported_suffixes": sorted(SUPPORTED_SUFFIXES),
    }
    return {
        "summary": summary,
        "findings": findings,
    }


def write_json_report(result: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan local evidence files for masked PII findings.")
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(DEFAULT_JSON_PATH),
        help="Path to JSON report output.",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not write a JSON report file.",
    )
    parser.add_argument(
        "--include-reports",
        action="store_true",
        help="Include supported files under reports/ in the scan target set.",
    )
    args = parser.parse_args()

    result = scan_files(include_reports=args.include_reports)
    print(f"Scanned files: {result['summary']['scanned_files']}")
    print(f"Sensitive findings: {result['summary']['sensitive_findings']}")

    if not args.no_json:
        output_path = write_json_report(result, Path(args.json_path))
        print(f"JSON report saved to: {output_path}")


if __name__ == "__main__":
    main()
