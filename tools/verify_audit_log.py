from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.integrity.audit_signer import verify_signed_audit_record
from backend.app.services.audit_service import LOG_FILE


def verify_audit_log(path: str | Path = LOG_FILE) -> dict[str, int]:
    log_path = Path(path)
    checked = 0
    valid = 0
    invalid = 0

    if not log_path.exists():
        return {"checked": 0, "valid": 0, "invalid": 0}

    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checked += 1
        record = json.loads(line)
        if verify_signed_audit_record(record):
            valid += 1
        else:
            invalid += 1
    return {"checked": checked, "valid": valid, "invalid": invalid}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed audit JSONL records.")
    parser.add_argument("--log-file", default=str(LOG_FILE), help="Path to audit_log.jsonl.")
    args = parser.parse_args()

    result = verify_audit_log(args.log_file)
    print(
        "Audit log verification: "
        f"checked={result['checked']} valid={result['valid']} invalid={result['invalid']}"
    )
    raise SystemExit(1 if result["invalid"] else 0)


if __name__ == "__main__":
    main()
