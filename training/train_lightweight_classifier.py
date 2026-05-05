from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from backend.app.models.model_config import (
    CLASSIFIER_PATH,
    DEFAULT_MODEL_VERSION,
    LIGHTWEIGHT_MODEL_DIR,
    METADATA_PATH,
    VECTORIZER_PATH,
)
from training.prepare_dataset import DEFAULT_OUTPUT_PATH as DEFAULT_DATASET_PATH
from training.prepare_dataset import build_dataset, write_jsonl
from training.split_dataset import DEFAULT_OUTPUT_DIR, assign_splits, load_jsonl, rewrite_dataset, write_splits

try:
    import joblib  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("joblib is required to train the lightweight classifier.") from exc

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.linear_model import LogisticRegression  # type: ignore
    from sklearn.metrics import classification_report  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn is required to train the lightweight classifier.") from exc


def _ensure_split_files(dataset_path: Path, output_dir: Path) -> dict[str, Path]:
    if not dataset_path.exists():
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(build_dataset(), dataset_path)

    expected_paths = {split: output_dir / f"{split}.jsonl" for split in ("train", "valid", "test")}
    if all(path.exists() for path in expected_paths.values()):
        return expected_paths

    records = load_jsonl(dataset_path)
    assigned = assign_splits(records)
    rewrite_dataset(assigned, dataset_path)
    outputs = write_splits(assigned, output_dir)
    return outputs


def _load_split(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def _label_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(record["label"]) for record in records))


def train_classifier(dataset_path: Path, output_dir: Path) -> dict[str, Any]:
    split_paths = _ensure_split_files(dataset_path, output_dir)
    train_records = _load_split(split_paths["train"])
    valid_records = _load_split(split_paths["valid"])
    test_records = _load_split(split_paths["test"])

    train_texts = [str(item["text"]) for item in train_records]
    train_labels = [str(item["label"]) for item in train_records]
    valid_texts = [str(item["text"]) for item in valid_records]
    valid_labels = [str(item["label"]) for item in valid_records]
    test_texts = [str(item["text"]) for item in test_records]
    test_labels = [str(item["label"]) for item in test_records]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=12000,
        min_df=1,
        sublinear_tf=True,
    )
    classifier = LogisticRegression(
        max_iter=1200,
        class_weight="balanced",
        solver="liblinear",
        multi_class="auto",
    )

    train_features = vectorizer.fit_transform(train_texts)
    classifier.fit(train_features, train_labels)

    valid_predictions = classifier.predict(vectorizer.transform(valid_texts))
    test_predictions = classifier.predict(vectorizer.transform(test_texts))
    valid_report = classification_report(valid_labels, valid_predictions, output_dict=True, zero_division=0)
    test_report = classification_report(test_labels, test_predictions, output_dict=True, zero_division=0)

    LIGHTWEIGHT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(classifier, CLASSIFIER_PATH)

    metadata = {
        "model_version": DEFAULT_MODEL_VERSION,
        "dataset_path": str(dataset_path),
        "split_paths": {name: str(path) for name, path in split_paths.items()},
        "train_distribution": _label_distribution(train_records),
        "valid_distribution": _label_distribution(valid_records),
        "test_distribution": _label_distribution(test_records),
        "valid_macro_f1": valid_report.get("macro avg", {}).get("f1-score", 0.0),
        "test_macro_f1": test_report.get("macro avg", {}).get("f1-score", 0.0),
    }
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the TF-IDF + Logistic Regression lightweight classifier.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Dataset JSONL path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Processed split directory.")
    args = parser.parse_args()

    metadata = train_classifier(Path(args.dataset), Path(args.output_dir))
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
