from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUTPUT = Path("data/external/attention_tracker/shared_prompt_injection_eval.csv")
DEFAULT_INSTRUCTION = "Say xxxxxx"
DEFAULT_LIMIT = 100
DEEPSET_DATASET = "deepset/prompt-injections"

PRIORITY_DIRS = [
    Path("data/evaluation"),
    Path("data/external"),
    Path("datasets"),
    Path("tests/fixtures"),
    Path("reports"),
]
KEYWORD_PATTERN = re.compile(
    r"prompt|injection|external|deepset|benchmark|eval|validation",
    re.IGNORECASE,
)
TEXT_COLUMNS = ["text", "prompt", "input", "query", "data", "instruction"]
LABEL_COLUMNS = [
    "label",
    "labels",
    "is_attack",
    "is_injection",
    "class",
    "expected_label",
    "expected_injection",
]


@dataclass(frozen=True, slots=True)
class NormalizedSample:
    source_file: Path
    original_id: str
    dataset: str
    text: str
    label: int


def normalize_label(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        if value in {0, 1}:
            return value
    if isinstance(value, float):
        as_int = int(value)
        if value == as_int and as_int in {0, 1}:
            return as_int
    if isinstance(value, list):
        joined = " ".join(str(item) for item in value).upper()
        if "INJ" in joined or "PROMPT_INJECTION" in joined:
            return 1
        if not joined.strip():
            return 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {
            "1",
            "true",
            "attack",
            "malicious",
            "injection",
            "prompt_injection",
            "prompt-injection",
            "inject",
        }:
            return 1
        if lowered in {
            "0",
            "false",
            "safe",
            "benign",
            "normal",
            "legit",
            "not_injection",
            "not injection",
            "notinject",
        }:
            return 0
    raise ValueError(f"Unsupported label value: {value!r}")


def find_first_key(row: dict[str, Any], candidates: list[str]) -> str | None:
    lookup = {str(key).lower(): key for key in row}
    for candidate in candidates:
        actual = lookup.get(candidate.lower())
        if actual is not None and row.get(actual) is not None:
            return str(actual)
    return None


def candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for priority, directory in enumerate(PRIORITY_DIRS):
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".csv", ".json", ".jsonl", ".md"}:
                continue
            if KEYWORD_PATTERN.search(path.name) or KEYWORD_PATTERN.search(str(path.relative_to(root))):
                files.append(path)

    def sort_key(path: Path) -> tuple[int, int, str]:
        relative = path.relative_to(root)
        priority = next(
            (index for index, directory in enumerate(PRIORITY_DIRS) if directory in relative.parents),
            len(PRIORITY_DIRS),
        )
        deepset_bias = 0 if "deepset" in str(relative).lower() else 1
        return priority, deepset_bias, str(relative).lower()

    return sorted(dict.fromkeys(files), key=sort_key)


def read_json_rows(path: Path) -> Iterable[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(data, dict):
        for key in ["rows", "samples", "data", "items"]:
            value = data.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield item
                return
        yield data


def read_jsonl_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                yield obj


def read_csv_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def rows_from_file(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        yield from read_jsonl_rows(path)
    elif suffix == ".json":
        yield from read_json_rows(path)
    elif suffix == ".csv":
        yield from read_csv_rows(path)


def normalize_rows(path: Path) -> list[NormalizedSample]:
    samples: list[NormalizedSample] = []
    for index, row in enumerate(rows_from_file(path), start=1):
        text_key = find_first_key(row, TEXT_COLUMNS)
        label_key = find_first_key(row, LABEL_COLUMNS)
        if text_key is None or label_key is None:
            continue

        try:
            label = normalize_label(row.get(label_key))
        except ValueError:
            continue

        text = str(row[text_key]).strip()
        if not text:
            continue

        dataset = str(row.get("dataset") or row.get("source") or "").strip()
        if "pii" in dataset.lower() or "pii" in path.name.lower():
            continue

        original_id = str(row.get("id") or index)
        samples.append(
            NormalizedSample(
                source_file=path,
                original_id=original_id,
                dataset=dataset,
                text=text,
                label=label,
            )
        )
    return samples


def deepset_sort_key(sample: NormalizedSample) -> tuple[int, int, str]:
    match = re.search(r"deepset-(train|test)-(\d+)", sample.original_id)
    if not match:
        return 99, 10**9, sample.original_id
    split_order = {"test": 0, "train": 1}
    return split_order.get(match.group(1), 99), int(match.group(2)), sample.original_id


def choose_samples(root: Path, limit: int | None) -> tuple[list[NormalizedSample], str]:
    all_samples: list[NormalizedSample] = []
    for path in candidate_files(root):
        all_samples.extend(normalize_rows(path))

    if not all_samples:
        raise RuntimeError("No prompt injection dataset candidates found.")

    deepset_samples = [
        sample
        for sample in all_samples
        if DEEPSET_DATASET in sample.dataset or DEEPSET_DATASET in sample.original_id
    ]
    if deepset_samples:
        selected = sorted(deepset_samples, key=deepset_sort_key)
        source = "Capstone GitHub dataset: datasets/external_splits deepset rows"
    else:
        grouped: dict[Path, list[NormalizedSample]] = {}
        for sample in all_samples:
            grouped.setdefault(sample.source_file, []).append(sample)
        valid_groups = [
            group
            for group in grouped.values()
            if {sample.label for sample in group} == {0, 1}
        ]
        if not valid_groups:
            raise RuntimeError("No binary prompt injection dataset with both labels found.")
        selected = max(valid_groups, key=len)
        source = f"Capstone GitHub dataset: {selected[0].source_file}"

    if limit is not None:
        selected = selected[:limit]

    labels = {sample.label for sample in selected}
    if labels != {0, 1}:
        raise RuntimeError(
            f"Selected dataset must contain both attack and benign labels; labels={sorted(labels)}"
        )
    return selected, source


def write_shared_csv(samples: list[NormalizedSample], output_path: Path, instruction: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text", "label", "instruction"])
        writer.writeheader()
        for index, sample in enumerate(samples, start=1):
            writer.writerow(
                {
                    "id": index,
                    "text": sample.text,
                    "label": sample.label,
                    "instruction": instruction,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--instruction", default=DEFAULT_INSTRUCTION)
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Default is subset-100 so Attention Tracker and capstone runs align.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    samples, source = choose_samples(root, limit=args.limit)
    output_path = Path(args.output_csv)
    write_shared_csv(samples, output_path, args.instruction)

    attacks = sum(1 for sample in samples if sample.label == 1)
    benign = len(samples) - attacks
    print(f"source={source}")
    print(f"output={output_path}")
    print(f"total={len(samples)} attacks={attacks} benign={benign}")
    print("scope=subset-100" if len(samples) == DEFAULT_LIMIT else "scope=custom")


if __name__ == "__main__":
    main()
