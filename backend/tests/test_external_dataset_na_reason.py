from __future__ import annotations

from evaluation.external_dataset_compare import (
    DatasetBundle,
    DatasetSpec,
    PreviousResult,
    _fmt,
    _na_reason,
    _na_result,
)


def test_fmt_none_as_na() -> None:
    assert _fmt(None) == "N/A"


def test_positive_only_reason_marks_precision_f1_not_applicable() -> None:
    reason = _na_reason("loaded", "enabled", positive_only=True)

    assert "positive_only_dataset" in reason


def test_model_unavailable_reason_is_explicit() -> None:
    assert _na_reason("loaded", "artifact_missing") == "model_artifact_missing"


def test_na_result_includes_reason_and_metric_scope() -> None:
    spec = DatasetSpec(
        name="example/unavailable",
        source="local",
        role="test dataset",
        loader=lambda split: [],
        previous=PreviousResult(
            size=0,
            precision=None,
            recall=0.0,
            f1=None,
            accuracy=0.0,
            tp=0,
            fp=None,
            tn=None,
            fn=None,
        ),
    )
    bundle = DatasetBundle(
        spec=spec,
        samples=[],
        status="unavailable",
        note="loader failed",
    )

    row = _na_result(bundle, "Lightweight Model Only", "artifact_missing")

    assert row["na_reason"] == "dataset_unavailable"
    assert row["metric_scope"] == "not_available"
