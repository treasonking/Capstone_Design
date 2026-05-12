from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets import Dataset, DatasetDict, load_dataset


@dataclass(frozen=True, slots=True)
class ExternalSample:
    id: str
    source: str
    text: str
    expected_injection: bool


PROTECTAI_DATASET_NAME = "protectai/prompt-injection-validation"
PROTECTAI_FALLBACK_DATASET_NAME = "Abdennebi/protectai-prompt-injection-validation"


def _first_existing_key(row: dict[str, Any], keys: list[str]) -> str | None:
    lowered_lookup = {str(key).lower(): key for key in row}
    for key in keys:
        actual_key = lowered_lookup.get(key.lower())
        if actual_key is not None and row[actual_key] is not None:
            return actual_key
    return None


def _normalize_label(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value == 1

    if isinstance(value, float):
        return int(value) == 1

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "inject", "injection", "malicious", "attack"}:
            return True
        if lowered in {
            "0",
            "false",
            "legit",
            "benign",
            "normal",
            "notinject",
            "not_injection",
            "not injection",
        }:
            return False

    raise ValueError(f"Unsupported label value: {value!r}")


def _load_dataset_dict(dataset_name: str) -> DatasetDict:
    loaded = load_dataset(dataset_name)
    if isinstance(loaded, DatasetDict):
        return loaded
    return DatasetDict({"train": loaded})


def _selected_splits(dataset_dict: DatasetDict, split: str) -> list[tuple[str, Dataset]]:
    if split in {"all", "*"}:
        return [(split_name, dataset) for split_name, dataset in dataset_dict.items()]

    if split not in dataset_dict:
        available = list(dataset_dict.keys())
        raise ValueError(f"Split '{split}' not found. Available splits: {available}")

    return [(split, dataset_dict[split])]


def _rows_from_dataset(
    dataset_name: str,
    split: str,
    fallback_dataset_name: str | None = None,
) -> list[tuple[str, int, dict[str, Any]]]:
    try:
        dataset_dict = _load_dataset_dict(dataset_name)
    except Exception:
        if fallback_dataset_name is None:
            raise
        dataset_dict = _load_dataset_dict(fallback_dataset_name)

    rows: list[tuple[str, int, dict[str, Any]]] = []
    for split_name, dataset in _selected_splits(dataset_dict, split):
        for idx, row in enumerate(dataset):
            rows.append((split_name, idx, dict(row)))
    return rows


def _sample_id(prefix: str, split_name: str, idx: int) -> str:
    normalized_split = split_name.lower().replace("_", "-")
    return f"{prefix}-{normalized_split}-{idx:05d}"


def _build_labeled_samples(
    *,
    dataset_name: str,
    id_prefix: str,
    split: str,
    fallback_dataset_name: str | None = None,
) -> list[ExternalSample]:
    samples: list[ExternalSample] = []
    rows = _rows_from_dataset(dataset_name, split, fallback_dataset_name)

    for split_name, idx, row in rows:
        text_key = _first_existing_key(row, ["text", "prompt", "query", "instruction"])
        label_key = _first_existing_key(row, ["label", "labels", "is_injection", "injection"])

        if text_key is None or label_key is None:
            raise KeyError(f"Unsupported {dataset_name} row schema: {row.keys()}")

        samples.append(
            ExternalSample(
                id=_sample_id(id_prefix, split_name, idx),
                source=dataset_name,
                text=str(row[text_key]),
                expected_injection=_normalize_label(row[label_key]),
            )
        )

    return samples


def load_deepset_prompt_injections(split: str = "all") -> list[ExternalSample]:
    return _build_labeled_samples(
        dataset_name="deepset/prompt-injections",
        id_prefix="deepset",
        split=split,
    )


def load_protectai_prompt_injection_validation(split: str = "all") -> list[ExternalSample]:
    return _build_labeled_samples(
        dataset_name=PROTECTAI_DATASET_NAME,
        id_prefix="protectai",
        split=split,
        fallback_dataset_name=PROTECTAI_FALLBACK_DATASET_NAME,
    )


def load_lakera_gandalf_ignore_instructions(split: str = "all") -> list[ExternalSample]:
    samples: list[ExternalSample] = []
    rows = _rows_from_dataset("Lakera/gandalf_ignore_instructions", split)

    for split_name, idx, row in rows:
        text_key = _first_existing_key(row, ["text", "prompt", "query", "instruction"])

        if text_key is None:
            raise KeyError(f"Unsupported Lakera row schema: {row.keys()}")

        samples.append(
            ExternalSample(
                id=_sample_id("lakera-gandalf", split_name, idx),
                source="Lakera/gandalf_ignore_instructions",
                text=str(row[text_key]),
                expected_injection=True,
            )
        )

    return samples
