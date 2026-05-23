"""Run HuggingFace text-guard classifiers on the shared baseline datasets.

This script is intended for guard models such as:

- meta-llama/Llama-Prompt-Guard-2-86M
- protectai/deberta-v3-base-prompt-injection
- protectai/deberta-v3-small-prompt-injection-v2
- leolee99/PIGuard
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


DATASET_KEYS = ["deepset", "protectai", "lakera"]
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_OUTPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_POSITIVE_LABELS = {
    "1",
    "label1",
    "label_1",
    "attack",
    "detected",
    "injection",
    "injectiondetected",
    "jailbreak",
    "malicious",
    "unsafe",
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
    return re.sub(r"[^a-z0-9_]+", "", label.strip().lower())


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def label_is_positive(label: str, positive_labels: set[str]) -> bool:
    normalized = normalize_label(label)
    if normalized in positive_labels:
        return True
    return any(token in normalized for token in ("injection", "jailbreak", "malicious", "unsafe", "attack"))


def score_prediction(
    labels: list[str],
    probabilities: list[float],
    positive_labels: set[str],
    threshold: float,
) -> tuple[int, float, str, float]:
    positive_score = sum(
        probability
        for label, probability in zip(labels, probabilities)
        if label_is_positive(label, positive_labels)
    )
    if positive_score == 0.0 and len(probabilities) == 2:
        # Most binary sequence classifiers expose LABEL_0/LABEL_1 when the model card
        # states 0=benign and 1=injection but id2label was not customized.
        positive_score = probabilities[1]

    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return (
        1 if positive_score >= threshold else 0,
        positive_score,
        labels[best_index],
        probabilities[best_index],
    )


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
    return Metrics(total=len(rows), tp=tp, fp=fp, tn=tn, fn=fn)


def fmt(value: float) -> str:
    return f"{value:.4f}"


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "label",
                "prediction",
                "score",
                "predicted_label",
                "predicted_score",
                "model_id",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, summary_rows: list[dict[str, str]]) -> None:
    lines = [
        "# HuggingFace Text-Guard Baseline Metrics",
        "",
        "| Dataset | Method | Model | Rows | Accuracy | Precision | Recall | F1 | TP | FP | TN | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {dataset} | {method} | `{model}` | {rows} | {accuracy} | {precision} | {recall} | {f1} | {tp} | {fp} | {tn} | {fn} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--method-key", required=True)
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
        help="Additional positive class label. Can be repeated.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "auto":
        device_name = "cpu"
    device = torch.device(device_name)

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id,
        trust_remote_code=args.trust_remote_code,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_id,
        trust_remote_code=args.trust_remote_code,
    )
    model.to(device)
    model.eval()

    id2label = {int(index): label for index, label in model.config.id2label.items()}
    ordered_labels = [id2label[index] for index in sorted(id2label)]
    positive_labels = set(DEFAULT_POSITIVE_LABELS)
    positive_labels.update(normalize_label(label) for label in args.positive_label)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    summary_rows: list[dict[str, str]] = []

    for dataset_key in DATASET_KEYS:
        input_path = input_dir / f"{dataset_key}_shared_eval.csv"
        source_rows = read_rows(input_path)
        output_rows: list[dict[str, str]] = []

        for start in range(0, len(source_rows), args.batch_size):
            batch_rows = source_rows[start : start + args.batch_size]
            texts = [row["text"] for row in batch_rows]
            encoded = tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=args.max_length,
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            with torch.no_grad():
                logits = model(**encoded).logits
                probabilities = torch.softmax(logits, dim=-1).detach().cpu().tolist()

            for source_row, probability_row in zip(batch_rows, probabilities):
                prediction, score, predicted_label, predicted_score = score_prediction(
                    ordered_labels,
                    probability_row,
                    positive_labels,
                    args.threshold,
                )
                output_rows.append(
                    {
                        "id": source_row["id"],
                        "label": str(int(source_row["label"])),
                        "prediction": str(prediction),
                        "score": f"{score:.8f}",
                        "predicted_label": predicted_label,
                        "predicted_score": f"{predicted_score:.8f}",
                        "model_id": args.model_id,
                    }
                )

        result_path = output_dir / f"{dataset_key}_{args.method_key}_results.csv"
        write_results(result_path, output_rows)
        metrics = compute_metrics(output_rows)
        summary_rows.append(
            {
                "dataset": dataset_key,
                "method": args.method_key,
                "model": args.model_id,
                "rows": str(metrics.total),
                "accuracy": fmt(metrics.accuracy),
                "precision": fmt(metrics.precision),
                "recall": fmt(metrics.recall),
                "f1": fmt(metrics.f1),
                "tp": str(metrics.tp),
                "fp": str(metrics.fp),
                "tn": str(metrics.tn),
                "fn": str(metrics.fn),
            }
        )
        print(
            f"{dataset_key}: rows={metrics.total} "
            f"accuracy={fmt(metrics.accuracy)} precision={fmt(metrics.precision)} "
            f"recall={fmt(metrics.recall)} f1={fmt(metrics.f1)} output={result_path}"
        )

    summary_path = output_dir / f"{args.method_key}_metrics.md"
    write_summary(summary_path, summary_rows)
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
