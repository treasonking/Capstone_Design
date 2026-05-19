"""
QA 기대값 vs 실제값 Diff 리포트 생성기

사용 예시:
  python diff_report.py --input results/test_result_YYYYMMDD_HHMMSS.json
  python diff_report.py --input results/test_result.json --output reports/qa_diff_report.html

입력 JSON은 아래 두 형태를 모두 지원합니다.
  1) [{...}, {...}]
  2) {"results": [{...}, {...}]}
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

STATUS_CLASSES = {
    "PASS": "pass",
    "FAIL": "fail",
    "ERROR": "error",
}


def as_list(value: Any) -> list[str]:
    """문자열/리스트/None을 화면 출력용 문자열 리스트로 정규화한다."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        if not value.strip():
            return []
        return [value]
    return [str(value)]


def safe_text(value: Any, default: str = "—") -> str:
    """HTML에 안전하게 넣을 수 있도록 문자열을 escape한다."""
    if value is None:
        return default
    text = str(value)
    return html.escape(text if text else default)


def short_text(value: Any, length: int = 60) -> str:
    text = "" if value is None else str(value)
    if len(text) <= length:
        return safe_text(text)
    return safe_text(text[:length] + "...")


def get_first(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """여러 버전의 결과 JSON 필드명을 호환하기 위한 getter."""
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def normalize_result(row: dict[str, Any]) -> dict[str, Any]:
    """테스트 결과 1건을 리포트 생성에 필요한 표준 필드로 변환한다."""
    expected_codes = as_list(
        get_first(row, "expected_codes_list", "expected_reason_codes", "expected_codes", default=[])
    )
    actual_codes = as_list(
        get_first(row, "actual_reason_codes", "reason_codes", "actual_codes", default=[])
    )

    expected_action = get_first(row, "expected_action", "expected", default="—")
    actual_action = get_first(row, "actual_action", "action", "actual", default="—")

    action_pass = row.get("action_pass")
    if action_pass is None and expected_action != "—" and actual_action != "—":
        action_pass = str(expected_action).upper() == str(actual_action).upper()

    codes_pass = row.get("codes_pass")
    if codes_pass is None:
        codes_pass = set(expected_codes) == set(actual_codes)

    status = str(row.get("status") or "").upper()
    if status not in STATUS_CLASSES:
        status = "PASS" if action_pass and codes_pass else "FAIL"

    return {
        "tc_id": get_first(row, "tc_id", "id", "case_id", default="—"),
        "description": get_first(row, "description", "title", "name", default=""),
        "category": get_first(row, "category", "type", default="UNCATEGORIZED"),
        "input_text": get_first(row, "input_text", "input", "prompt", "text", default=""),
        "expected_action": expected_action,
        "actual_action": actual_action,
        "expected_codes_list": expected_codes,
        "actual_reason_codes": actual_codes,
        "action_pass": bool(action_pass),
        "codes_pass": bool(codes_pass),
        "status": status,
        "latency_ms": get_first(row, "latency_ms", "elapsed_ms", "duration_ms", default="—"),
        "error": get_first(row, "error", "message", default=""),
    }


def load_results(input_path: Path) -> list[dict[str, Any]]:
    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")

    with input_path.open(encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("results") or data.get("test_results") or data.get("cases")

    if not isinstance(data, list):
        raise ValueError("입력 JSON은 리스트이거나 results/test_results/cases 키를 가진 객체여야 합니다.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{index}번째 결과가 객체(dict)가 아닙니다.")
        normalized.append(normalize_result(item))
    return normalized


def build_table_rows(results: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for row in results:
        status_class = STATUS_CLASSES.get(row["status"], "")
        exp_codes = safe_text(", ".join(row["expected_codes_list"]) if row["expected_codes_list"] else "—"
        )
        act_codes = safe_text(", ".join(row["actual_reason_codes"]) if row["actual_reason_codes"] else "—")
        action_diff = "" if row["action_pass"] else " ⚠️"
        codes_diff = "" if row["codes_pass"] else " ⚠️"
        error_note = f"<div class='error-note'>{safe_text(row['error'])}</div>" if row["error"] else ""

        rows.append(
            f"""
            <tr class="{status_class}">
              <td>{safe_text(row['tc_id'])}</td>
              <td><span class="cat-badge">{safe_text(row['category'])}</span></td>
              <td class="input-cell" title="{safe_text(row['input_text'])}">{short_text(row['input_text'])}{error_note}</td>
              <td>{safe_text(row['expected_action'])}</td>
              <td>{safe_text(row['actual_action'])}{action_diff}</td>
              <td>{exp_codes}</td>
              <td>{act_codes}{codes_diff}</td>
              <td><span class="status-badge {status_class}">{safe_text(row['status'])}</span></td>
              <td>{safe_text(row['latency_ms'])}</td>
            </tr>"""
        )
    return "\n".join(rows)


def generate_html_report(results: list[dict[str, Any]], output_path: Path) -> None:
    total = len(results)
    passed = sum(1 for row in results if row["status"] == "PASS")
    failed = sum(1 for row in results if row["status"] == "FAIL")
    errors = sum(1 for row in results if row["status"] == "ERROR")
    pass_rate = passed / total * 100 if total else 0.0

    category_total = Counter(row["category"] for row in results)
    category_fail = Counter(row["category"] for row in results if row["status"] == "FAIL")

    failed_reason_codes: list[str] = []
    for row in results:
        if row["status"] == "FAIL":
            # 실패 원인은 실제 탐지 코드 기준으로 보는 게 디버깅에 더 유용하다.
            failed_reason_codes.extend(row["actual_reason_codes"] or row["expected_codes_list"])
    reason_code_counter = Counter(failed_reason_codes)

    category_rows = "\n".join(
        f"<tr><td>{safe_text(category)}</td><td>{count}</td><td>{category_fail.get(category, 0)}</td><td>{count - category_fail.get(category, 0)}</td></tr>"
        for category, count in sorted(category_total.items())
    )
    reason_rows = "\n".join(
        f"<tr><td>{safe_text(code)}</td><td>{count}</td></tr>"
        for code, count in reason_code_counter.most_common()
    )
    reason_section = (
        "<div class='section'><h2>실패 다발 reason_code</h2>"
        "<table><thead><tr><th>reason_code</th><th>실패 건수</th></tr></thead>"
        f"<tbody>{reason_rows}</tbody></table></div>"
        if reason_rows
        else ""
    )

    generated_at = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
    html_doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QA Diff Report</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Arial, 'Malgun Gothic', sans-serif; background: #f0f2f5; color: #1a1a2e; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 32px 40px; }}
  .header h1 {{ margin: 0; font-size: 1.8rem; }}
  .header p {{ margin: 8px 0 0; color: #cbd5e1; font-size: .9rem; }}
  .container {{ padding: 32px 40px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: white; border-radius: 12px; padding: 22px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .card .num {{ font-size: 2.2rem; font-weight: 800; }}
  .card .label {{ color: #64748b; margin-top: 4px; }}
  .total .num {{ color: #2563eb; }} .pass .num {{ color: #16a34a; }} .fail .num {{ color: #dc2626; }} .error .num {{ color: #d97706; }}
  .progress {{ height: 12px; background: #e2e8f0; border-radius: 99px; overflow: hidden; margin-top: 10px; }}
  .progress-bar {{ height: 100%; width: {pass_rate:.1f}%; background: linear-gradient(90deg, #22c55e, #16a34a); }}
  .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,.08); overflow-x: auto; }}
  .section h2 {{ margin: 0 0 16px; font-size: 1rem; border-left: 4px solid #3b82f6; padding-left: 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85rem; min-width: 860px; }}
  th {{ background: #f8fafc; padding: 10px 12px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  tr.pass td {{ background: #f0fdf4; }} tr.fail td {{ background: #fef2f2; }} tr.error td {{ background: #fffbeb; }}
  .status-badge, .cat-badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; }}
  .status-badge.pass {{ background: #dcfce7; color: #166534; }}
  .status-badge.fail {{ background: #fee2e2; color: #991b1b; }}
  .status-badge.error {{ background: #fef9c3; color: #854d0e; }}
  .cat-badge {{ background: #e0e7ff; color: #3730a3; }}
  .input-cell {{ font-family: Consolas, monospace; color: #334155; max-width: 360px; }}
  .error-note {{ margin-top: 6px; color: #b91c1c; font-family: Arial, 'Malgun Gothic', sans-serif; }}
</style>
</head>
<body>
  <div class="header">
    <h1>LLM 보안 프록시 QA Diff Report</h1>
    <p>생성일시: {generated_at} | 총 {total}개 테스트 케이스</p>
  </div>
  <main class="container">
    <section class="summary-grid">
      <div class="card total"><div class="num">{total}</div><div class="label">전체 케이스</div></div>
      <div class="card pass"><div class="num">{passed}</div><div class="label">PASS</div><div class="progress"><div class="progress-bar"></div></div><div class="label">{pass_rate:.1f}%</div></div>
      <div class="card fail"><div class="num">{failed}</div><div class="label">FAIL</div></div>
      <div class="card error"><div class="num">{errors}</div><div class="label">ERROR</div></div>
    </section>

    <div class="section">
      <h2>카테고리별 결과</h2>
      <table><thead><tr><th>카테고리</th><th>전체</th><th>FAIL</th><th>PASS/ERROR</th></tr></thead><tbody>{category_rows}</tbody></table>
    </div>

    {reason_section}

    <div class="section">
      <h2>전체 테스트 케이스 상세</h2>
      <table>
        <thead><tr><th>ID</th><th>카테고리</th><th>입력</th><th>기대 Action</th><th>실제 Action</th><th>기대 Codes</th><th>실제 Codes</th><th>결과</th><th>지연(ms)</th></tr></thead>
        <tbody>{build_table_rows(results)}</tbody>
      </table>
    </div>
  </main>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")


def print_diff_summary(results: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 70)
    print("DIFF 요약 (기대값 vs 실제값)")
    print("=" * 70)

    has_diff = False
    for row in results:
        if row["status"] == "PASS":
            continue
        has_diff = True
        print(f"\n[{row['tc_id']}] {row['description'] or row['category']}")
        if not row["action_pass"]:
            print(f"  Action 기대: {row['expected_action']} -> 실제: {row['actual_action']}")
        if not row["codes_pass"]:
            expected = row["expected_codes_list"]
            actual = row["actual_reason_codes"]
            missing = [code for code in expected if code not in actual]
            extra = [code for code in actual if code not in expected]
            if missing:
                print(f"  Codes 누락: {missing}")
            if extra:
                print(f"  Codes 추가: {extra}")
        if row["error"]:
            print(f"  Error: {row['error']}")

    if not has_diff:
        print("모든 테스트 케이스가 PASS입니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA Diff 리포트 생성기")
    parser.add_argument("--input", required=True, help="qa_runner/evaluation 결과 JSON 파일 경로")
    parser.add_argument("--output", default=None, help="HTML 리포트 출력 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_report.html")

    results = load_results(input_path)
    generate_html_report(results, output_path)
    print_diff_summary(results)
    print(f"\nHTML 리포트 저장: {output_path}\n")


if __name__ == "__main__":
    main()
