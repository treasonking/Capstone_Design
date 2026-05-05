from __future__ import annotations

from collections import Counter

from training.prepare_dataset import build_dataset
from training.split_dataset import assign_splits


def test_dataset_schema_has_required_fields() -> None:
    sample = build_dataset()[0]
    required_fields = {
        "id",
        "text",
        "label",
        "pii_types",
        "injection_types",
        "expected_action",
        "source",
        "domain",
        "difficulty",
        "split",
        "template_id",
    }

    assert required_fields.issubset(sample.keys())


def test_dataset_split_assignment_keeps_expected_splits() -> None:
    records = assign_splits(build_dataset())
    split_counts = Counter(str(record["split"]) for record in records)

    assert split_counts["train"] > 0
    assert split_counts["valid"] > 0
    assert split_counts["test"] > 0


def test_dataset_labels_cover_hybrid_categories() -> None:
    labels = {str(record["label"]) for record in build_dataset()}
    assert labels == {"safe", "pii_risk", "injection_risk", "mixed_risk", "edge_case"}
