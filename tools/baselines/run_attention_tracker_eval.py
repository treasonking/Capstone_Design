from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


MODEL_NAME_ALIASES = {
    "Qwen/Qwen2-1.5B-Instruct": "qwen2-attn",
    "qwen2": "qwen2-attn",
    "qwen2-1.5b": "qwen2-attn",
    "qwen2-attn": "qwen2-attn",
}
DEFAULT_REPO_CANDIDATES = [
    Path("external/attention-tracker/Attention-Tracker"),
    Path("../Attention-Tracker-main/external/attention-tracker/Attention-Tracker"),
    Path("../Attention-Tracker-main/Attention-Tracker-main"),
]


def read_dataset(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        required = {"id", "label", "instruction"}
        if not ({"text"} <= fieldnames or {"data"} <= fieldnames):
            raise ValueError("Input CSV must contain either a text or data column.")
        missing = required - fieldnames
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        rows = list(reader)
    return rows[:limit] if limit is not None else rows


def row_text(row: dict[str, str]) -> str:
    return (row.get("text") or row.get("data") or "").strip()


def normalize_prediction(value: Any, default: int) -> int:
    text = str(value).strip().lower()
    if text in {"1", "true", "attack", "injection", "malicious", "unsafe", "reject"}:
        return 1
    if text in {"0", "false", "benign", "normal", "safe", "accept"}:
        return 0
    return default


def parse_attention_tracker_stdout(stdout: str, threshold: float) -> tuple[float, int, dict[str, Any]]:
    text = stdout.strip()
    lower = text.lower()
    metadata: dict[str, Any] = {"raw_stdout": text[-2000:], "parser": None}

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for key in ["score", "focus_score", "fs", "FS"]:
                if key in obj:
                    score = float(obj[key])
                    pred = 1 if score < threshold else 0
                    if "prediction" in obj:
                        pred = normalize_prediction(obj["prediction"], default=pred)
                    metadata["parser"] = "json"
                    return score, pred, metadata
    except Exception:
        pass

    score_patterns = [
        r"focus[_\s-]*score\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
        r"\bfs\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
        r"\bscore\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
        r"\battention\s*score\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
    ]
    score: float | None = None
    for pattern in score_patterns:
        match = re.search(pattern, lower)
        if match:
            score = float(match.group(1))
            metadata["parser"] = f"regex:{pattern}"
            break

    pred: int | None = None
    official_match = re.search(
        r"is\s+prompt\s+injection\s+detected\?\s*(true|false|1|0|yes|no)",
        lower,
    )
    if official_match:
        pred = normalize_prediction(official_match.group(1), default=0)
        metadata["prediction_parser"] = "official-run.py"
    elif re.search(r"\bprediction\s*[:=]\s*(attack|injection|malicious|unsafe|reject|true|1)\b", lower):
        pred = 1
    elif re.search(r"\bprediction\s*[:=]\s*(benign|normal|safe|accept|false|0)\b", lower):
        pred = 0

    if score is None and pred is None:
        raise ValueError("Could not parse score or prediction from Attention Tracker stdout")
    if score is None:
        score = float(pred)
    if pred is None:
        pred = 1 if score < threshold else 0
    return score, pred, metadata


def resolve_repo_dir(repo_dir: Path | None) -> Path:
    candidates = [repo_dir] if repo_dir is not None else DEFAULT_REPO_CANDIDATES
    for candidate in candidates:
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if (resolved / "run.py").exists():
            return resolved
    formatted = ", ".join(str(path) for path in DEFAULT_REPO_CANDIDATES)
    raise FileNotFoundError(f"Attention Tracker repo not found. Tried: {formatted}")


def resolve_model_name(repo_dir: Path, model_name: str) -> str:
    mapped = MODEL_NAME_ALIASES.get(model_name, model_name)
    config_path = repo_dir / "configs" / "model_configs" / f"{mapped}_config.json"
    if config_path.exists():
        return mapped
    direct = repo_dir / "configs" / "model_configs" / f"{model_name}_config.json"
    if direct.exists():
        return model_name
    available = sorted(
        path.name.removesuffix("_config.json")
        for path in (repo_dir / "configs" / "model_configs").glob("*_config.json")
    )
    raise ValueError(f"Could not resolve model config for {model_name!r}; available={available}")


def build_direct_detector(repo_dir: Path, model_name: str, threshold: float):
    sys.path.insert(0, str(repo_dir))
    try:
        utils = importlib.import_module("utils")
        detector_module = importlib.import_module("detector.attn")
        official_model_name = resolve_model_name(repo_dir, model_name)
        config = utils.open_config(
            config_path=str(repo_dir / "configs" / "model_configs" / f"{official_model_name}_config.json")
        )
        model = utils.create_model(config=config)
        detector = detector_module.AttentionDetector(model, threshold=threshold)
        return detector, official_model_name
    finally:
        if sys.path and sys.path[0] == str(repo_dir):
            sys.path.pop(0)


def write_result_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=["id", "label", "score", "prediction"]).writeheader()


def append_result(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "label", "score", "prediction"])
        writer.writerow(row)


def write_error_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "label", "error", "query_preview", "stdout_tail"],
        )
        writer.writeheader()


def append_error(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "label", "error", "query_preview", "stdout_tail"],
        )
        writer.writerow(row)


def evaluate_direct(
    *,
    repo_dir: Path,
    input_rows: list[dict[str, str]],
    output_csv: Path,
    error_csv: Path,
    model_name: str,
    threshold: float,
) -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    detector, official_model_name = build_direct_detector(repo_dir, model_name, threshold)
    write_result_header(output_csv)
    write_error_header(error_csv)

    success_count = 0
    error_count = 0
    for index, row in enumerate(input_rows, start=1):
        text = row_text(row)
        try:
            detected, metadata = detector.detect(text)
            score = float(metadata["focus_score"])
            prediction = 1 if score < threshold else 0
            append_result(
                output_csv,
                {
                    "id": row["id"],
                    "label": int(row["label"]),
                    "score": f"{score:.8f}",
                    "prediction": prediction,
                },
            )
            success_count += 1
            print(
                f"[OK] {index}/{len(input_rows)} id={row['id']} "
                f"label={row['label']} score={score:.6f} pred={prediction} model={official_model_name}"
            )
        except Exception as exc:
            error_count += 1
            append_error(
                error_csv,
                {
                    "id": row.get("id", ""),
                    "label": row.get("label", ""),
                    "error": str(exc)[-2000:],
                    "query_preview": text[:500],
                    "stdout_tail": "",
                },
            )
            print(f"[ERROR] {index}/{len(input_rows)} id={row.get('id')} {exc}")

    print(f"[DONE] success={success_count}, errors={error_count}")
    if success_count == 0:
        raise RuntimeError("Attention Tracker evaluation produced zero result rows.")


def read_csv_by_id(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def import_precomputed(
    *,
    input_rows: list[dict[str, str]],
    output_csv: Path,
    error_csv: Path,
    precomputed_csv: Path,
    precomputed_error_csv: Path | None,
    threshold: float,
) -> None:
    precomputed = read_csv_by_id(precomputed_csv)
    valid_ids = {row["id"] for row in input_rows}
    label_by_id = {row["id"]: int(row["label"]) for row in input_rows}

    write_result_header(output_csv)
    success_count = 0
    for sample_id in [row["id"] for row in input_rows]:
        row = precomputed.get(sample_id)
        if row is None:
            continue
        score = float(row["score"])
        append_result(
            output_csv,
            {
                "id": sample_id,
                "label": label_by_id[sample_id],
                "score": f"{score:.8f}",
                "prediction": 1 if score < threshold else 0,
            },
        )
        success_count += 1

    write_error_header(error_csv)
    error_count = 0
    if precomputed_error_csv is not None and precomputed_error_csv.exists():
        with precomputed_error_csv.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("id") in valid_ids:
                    append_error(
                        error_csv,
                        {
                            "id": row.get("id", ""),
                            "label": row.get("label", label_by_id.get(row.get("id", ""), "")),
                            "error": row.get("error", ""),
                            "query_preview": row.get("query_preview", ""),
                            "stdout_tail": row.get("stdout_tail", ""),
                        },
                    )
                    error_count += 1

    print(f"[DONE] imported_success={success_count}, imported_errors={error_count}")
    print(f"[INFO] threshold={threshold} predictions recomputed from focus_score < threshold")
    if success_count == 0:
        raise RuntimeError(f"No matching precomputed rows found in {precomputed_csv}")


def run_mock(
    *,
    input_rows: list[dict[str, str]],
    output_csv: Path,
    error_csv: Path,
    threshold: float,
) -> None:
    write_result_header(output_csv)
    write_error_header(error_csv)
    for row in input_rows:
        label = int(row["label"])
        score = 0.1 if label == 1 else 0.9
        append_result(
            output_csv,
            {
                "id": row["id"],
                "label": label,
                "score": f"{score:.8f}",
                "prediction": 1 if score < threshold else 0,
            },
        )
    print("[DONE] mock results generated. Do not use mock output in reports.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", default=None)
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--error-csv", default="reports/baselines/attention_tracker_errors.csv")
    parser.add_argument("--model", default="Qwen/Qwen2-1.5B-Instruct")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.12)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--mode",
        choices=["direct", "precomputed", "mock"],
        default="direct",
        help="direct loads the official Attention Tracker once; precomputed imports prior real outputs.",
    )
    parser.add_argument("--precomputed-csv", default=None)
    parser.add_argument("--precomputed-error-csv", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_rows = read_dataset(Path(args.input_csv), limit=args.limit)
    if not input_rows:
        raise ValueError(f"No rows found in {args.input_csv}")

    output_csv = Path(args.output_csv)
    error_csv = Path(args.error_csv)
    if args.mode == "direct":
        repo_dir = resolve_repo_dir(Path(args.repo_dir) if args.repo_dir else None)
        evaluate_direct(
            repo_dir=repo_dir,
            input_rows=input_rows,
            output_csv=output_csv,
            error_csv=error_csv,
            model_name=args.model,
            threshold=args.threshold,
        )
    elif args.mode == "precomputed":
        if args.precomputed_csv is None:
            raise ValueError("--precomputed-csv is required for --mode precomputed")
        import_precomputed(
            input_rows=input_rows,
            output_csv=output_csv,
            error_csv=error_csv,
            precomputed_csv=Path(args.precomputed_csv),
            precomputed_error_csv=(
                Path(args.precomputed_error_csv)
                if args.precomputed_error_csv
                else None
            ),
            threshold=args.threshold,
        )
    else:
        run_mock(
            input_rows=input_rows,
            output_csv=output_csv,
            error_csv=error_csv,
            threshold=args.threshold,
        )


if __name__ == "__main__":
    main()
