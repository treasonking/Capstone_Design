from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "proxy.db")
DEFAULT_JSON_OUTPUT = os.path.join(PROJECT_ROOT, "reports", "scanner_result.json")

PII_PATTERNS = {
    "unmasked_mobile_phone": re.compile(r"(?<!\d)010[- .]?\d{4}[- .]?\d{4}(?!\d)"),
    "unmasked_rrn": re.compile(r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)"),
    "unmasked_email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "possible_bank_account": re.compile(r"(?<!\d)\d{2,6}[- ]\d{2,6}[- ]\d{5,8}(?!\d)"),
}

MASK_HINT_PATTERN = re.compile(r"\*|x{2,}|X{2,}|masked|redacted|마스킹")
TEXT_DECLARED_TYPES = ("CHAR", "CLOB", "TEXT", "VARCHAR", "NVARCHAR")


def _line_excerpt(text: str, start: int, end: int, radius: int = 36) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].replace("\n", "\\n")


def _looks_masked(value: str) -> bool:
    return bool(MASK_HINT_PATTERN.search(value))


def find_sensitive_values(text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not text:
        return findings

    for pattern_name, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            matched_value = match.group(0)
            if _looks_masked(matched_value):
                continue
            findings.append(
                {
                    "pattern": pattern_name,
                    "matched": matched_value,
                    "excerpt": _line_excerpt(text, match.start(), match.end()),
                }
            )
    return findings


def scan_logs(log_dir: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not os.path.isdir(log_dir):
        return findings

    for current_dir, _, file_names in os.walk(log_dir):
        for file_name in file_names:
            if not file_name.endswith(".log"):
                continue
            path = os.path.join(current_dir, file_name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as file:
                    for line_number, line in enumerate(file, start=1):
                        for finding in find_sensitive_values(line):
                            findings.append(
                                {
                                    "source": "log",
                                    "path": os.path.relpath(path, PROJECT_ROOT),
                                    "line": str(line_number),
                                    **finding,
                                }
                            )
            except OSError as exc:
                findings.append(
                    {
                        "source": "log",
                        "path": os.path.relpath(path, PROJECT_ROOT),
                        "line": "",
                        "pattern": "read_error",
                        "matched": str(exc),
                        "excerpt": "",
                    }
                )
    return findings


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _text_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    columns: list[str] = []
    cursor.execute(f"PRAGMA table_info({_quote_identifier(table_name)})")
    for row in cursor.fetchall():
        column_name = row[1]
        declared_type = str(row[2] or "").upper()
        if not declared_type or any(type_name in declared_type for type_name in TEXT_DECLARED_TYPES):
            columns.append(column_name)
    return columns


def scan_database(db_path: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not os.path.exists(db_path):
        return findings

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        table_names = [row[0] for row in cursor.fetchall()]

        audit_tables = [name for name in table_names if "audit" in name.lower() or "log" in name.lower()]
        scan_tables = audit_tables or table_names

        for table_name in scan_tables:
            columns = _text_columns(cursor, table_name)
            if not columns:
                continue

            selected_columns = ", ".join(_quote_identifier(column) for column in columns)
            cursor.execute(f"SELECT rowid, {selected_columns} FROM {_quote_identifier(table_name)}")
            for row in cursor.fetchall():
                rowid = row[0]
                for column_name, value in zip(columns, row[1:]):
                    if value is None:
                        continue
                    for finding in find_sensitive_values(str(value)):
                        findings.append(
                            {
                                "source": "database",
                                "path": os.path.relpath(db_path, PROJECT_ROOT),
                                "line": f"{table_name}.rowid={rowid}.{column_name}",
                                **finding,
                            }
                        )
    finally:
        connection.close()
    return findings


def run_scan(log_dir: str = DEFAULT_LOG_DIR, db_path: str = DEFAULT_DB_PATH) -> dict[str, object]:
    log_findings = scan_logs(log_dir)
    db_findings = scan_database(db_path)
    findings = log_findings + db_findings
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not findings else "FAIL",
        "sensitive_findings_count": len(findings),
        "log_findings_count": len(log_findings),
        "db_findings_count": len(db_findings),
        "log_dir": os.path.relpath(log_dir, PROJECT_ROOT) if os.path.isabs(log_dir) else log_dir,
        "db_path": os.path.relpath(db_path, PROJECT_ROOT) if os.path.isabs(db_path) else db_path,
        "findings": findings,
    }


def write_json_report(result: dict[str, object], output_path: str) -> None:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan logs and SQLite audit data for unmasked sensitive values.")
    parser.add_argument("--logs-dir", default=DEFAULT_LOG_DIR, help="Directory containing .log files. Default: logs/")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path. Default: proxy.db")
    parser.add_argument("--json-output", default=DEFAULT_JSON_OUTPUT, help="Where to write scanner JSON output.")
    parser.add_argument("--no-json", action="store_true", help="Do not write scanner JSON output.")
    args = parser.parse_args()

    result = run_scan(args.logs_dir, args.db)
    if not args.no_json:
        write_json_report(result, args.json_output)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
