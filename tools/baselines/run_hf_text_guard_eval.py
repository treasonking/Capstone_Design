"""Run HuggingFace text-guard classifiers on shared prompt-injection CSVs.

The primary interface evaluates one CSV at a time:

    python tools/baselines/run_hf_text_guard_eval.py \
        --input-csv reports/baselines/multi_dataset/deepset_shared_eval.csv \
        --output-csv reports/baselines/multi_dataset/deepset_protectai_detector_results.csv \
        --model protectai/deberta-v3-small-prompt-injection-v2

The legacy directory mode is still supported with ``--input-dir``,
``--output-dir``, and ``--method-key``.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATASET_KEYS = ("deepset", "protectai", "lakera")
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_OUTPUT_DIR = Path("reports/baselines/multi_dataset")

ATTACK_LABELS = {
    "1",
    "attack",
    "detected",
    "injection",
    "jailbreak",
    "label1",
    "label_1",
    "malicious",
    "promptinjection",
    "prompt_injection",
    "unsafe",
}
BENIGN_LABELS = {
    "0",
    "benign",
    "clean",
    "label0",
    "label_0",
    "noinjection",
    "no_injection",
    "normal",
    "notinjection",
    "not_injection",
    "safe",
}


@dataclass(frozen=True, slots=True)
class Metrics:
    total: int
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom else 0.0


def normalize_label(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", label.strip().lower())
    return normalized.strip("_")


def compact_label(label: str) -> str:
    return normalize_label(label).replace("_", "")


def model_label_class(label: str, extra_attack_labels: set[str]) -> int | None:
    normalized = normalize_label(label)
    compact = compact_label(label)
    attack_labels = ATTACK_LABELS | extra_attack_labels

    if normalized in BENIGN_LABELS or compact in BENIGN_LABELS:
        return 0
    if normalized in attack_labels or compact in attack_labels:
        return 1
    if "no_injection" in normalized or "not_injection" in normalized:
        return 0
    if any(token in normalized for token in ("jailbreak", "malicious", "unsafe", "attack")):
        return 1
    if "injection" in normalized:
        return 1
    return None


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"id", "text", "label"}
    missing = required - set(rows[0].keys() if rows else ())
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required column(s): {missing_list}")
    return rows


def infer_dataset_key(input_path: Path, rows: list[dict[str, str]]) -> str:
    stem = input_path.stem.lower()
    for key in DATASET_KEYS:
        if stem.startswith(key):
            return key
    if rows:
        value = rows[0].get("dataset", "").strip()
        if value:
            return value.split("/", 1)[0]
    return input_path.stem


def id2label_from_model(model: object) -> list[str]:
    config = model.config
    raw_id2label = getattr(config, "id2label", None) or {}
    if raw_id2label:
        pairs = sorted((int(index), label) for index, label in raw_id2label.items())
        return [str(label) for _, label in pairs]
    num_labels = int(getattr(config, "num_labels", 2))
    return [f"LABEL_{index}" for index in range(num_labels)]


def attack_score_from_probabilities(
    labels: list[str],
    probabilities: list[float],
    extra_attack_labels: set[str],
) -> tuple[float, str]:
    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    raw_label = labels[best_index] if best_index < len(labels) else f"LABEL_{best_index}"

    class_map = [model_label_class(label, extra_attack_labels) for label in labels]
    attack_indices = [index for index, klass in enumerate(class_map) if klass == 1]
    benign_indices = [index for index, klass in enumerate(class_map) if klass == 0]

    if attack_indices:
        return sum(probabilities[index] for index in attack_indices), raw_label
    if len(probabilities) == 2:
        if benign_indices:
            benign_score = sum(probabilities[index] for index in benign_indices)
            return 1.0 - benign_score, raw_label
        return probabilities[1], raw_label
    if benign_indices and best_index in benign_indices:
        return 1.0 - probabilities[best_index], raw_label
    return probabilities[best_index], raw_label


def iter_batches(rows: list[dict[str, str]], batch_size: int) -> Iterable[list[dict[str, str]]]:
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def compute_metrics(rows: list[dict[str, str]]) -> Metrics:
    tp = fp = tn = fn = 0
    for row in rows:
        label = int(row["label"])
        prediction = int(row["prediction"])
        if label == 1 and prediction == 1:
            tp += 1
        elif label == 0 and prediction == 1:
            fp += 1
        elif label == 0 and prediction == 0:
            tn += 1
        elif label == 1 and prediction == 0:
            fn += 1
    return Metrics(len(rows), tp, fp, tn, fn)


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "dataset",
                "label",
                "score",
                "prediction",
                "raw_label",
                "model_name",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def evaluate_csv(
    *,
    input_csv: Path,
    output_csv: Path,
    model_name: str,
    threshold: float,
    batch_size: int,
    max_length: int,
    device_name: str,
    trust_remote_code: bool,
    extra_attack_labels: set[str],
) -> Metrics:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=trust_remote_code,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        trust_remote_code=trust_remote_code,
    )
    model.to(device)
    model.eval()

    labels = id2label_from_model(model)
    source_rows = read_rows(input_csv)
    dataset_key = infer_dataset_key(input_csv, source_rows)
    output_rows: list[dict[str, str]] = []

    for batch_rows in iter_batches(source_rows, batch_size):
        texts = [row["text"] for row in batch_rows]
        encoded = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
            if logits.shape[-1] == 1:
                probabilities = torch.sigmoid(logits).detach().cpu().tolist()
            else:
                probabilities = torch.softmax(logits, dim=-1).detach().cpu().tolist()

        for source_row, probability_row in zip(batch_rows, probabilities):
            if len(probability_row) == 1:
                raw_label = labels[0] if labels else "LABEL_0"
                label_class = model_label_class(raw_label, extra_attack_labels)
                probability = float(probability_row[0])
                attack_score = 1.0 - probability if label_class == 0 else probability
            else:
                attack_score, raw_label = attack_score_from_probabilities(
                    labels,
                    [float(value) for value in probability_row],
                    extra_attack_labels,
                )
            prediction = 1 if attack_score >= threshold else 0
            output_rows.append(
                {
                    "id": source_row["id"],
                    "dataset": dataset_key,
                    "label": str(int(source_row["label"])),
                    "score": f"{attack_score:.8f}",
                    "prediction": str(prediction),
                    "raw_label": raw_label,
                    "model_name": model_name,
                }
            )

    write_results(output_csv, output_rows)
    return compute_metrics(output_rows)


def fmt(value: float) -> str:
    return f"{value:.4f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv")
    parser.add_argument("--output-csv")
    parser.add_argument("--model", "--model-id", dest="model")
    parser.add_argument("--method-key")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument(
        "--positive-label",
        action="append",
        default=[],
        help="Additional attack class label. Can be repeated.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.model:
        raise SystemExit("--model is required")
    if bool(args.input_csv) != bool(args.output_csv):
        raise SystemExit("--input-csv and --output-csv must be supplied together")
    if not args.input_csv and not args.method_key:
        raise SystemExit("--method-key is required when running directory mode")


def main() -> None:
    args = parse_args()
    validate_args(args)
    extra_attack_labels = {normalize_label(label) for label in args.positive_label}

    jobs: list[tuple[Path, Path]]
    if args.input_csv:
        jobs = [(Path(args.input_csv), Path(args.output_csv))]
    else:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir)
        jobs = [
            (
                input_dir / f"{dataset_key}_shared_eval.csv",
                output_dir / f"{dataset_key}_{args.method_key}_results.csv",
            )
            for dataset_key in DATASET_KEYS
        ]

    for input_csv, output_csv in jobs:
        metrics = evaluate_csv(
            input_csv=input_csv,
            output_csv=output_csv,
            model_name=args.model,
            threshold=args.threshold,
            batch_size=args.batch_size,
            max_length=args.max_length,
            device_name=args.device,
            trust_remote_code=args.trust_remote_code,
            extra_attack_labels=extra_attack_labels,
        )
        print(
            f"{input_csv}: rows={metrics.total} accuracy={fmt(metrics.accuracy)} "
            f"precision={fmt(metrics.precision)} recall={fmt(metrics.recall)} "
            f"f1={fmt(metrics.f1)} output={output_csv}"
        )


if __name__ == "__main__":
    main()
