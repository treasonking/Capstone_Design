from evaluation.latency_benchmark import LatencyMeasurement, _percentile, _summary_rows


def test_percentile_uses_nearest_rank() -> None:
    assert _percentile([1.0, 2.0, 3.0, 4.0], 95) == 4.0


def test_summary_rows_include_proxy_average_response_time() -> None:
    rows = _summary_rows(
        [
            LatencyMeasurement("proxy_end_to_end", "safe", "ALLOW", 1, 10.0),
            LatencyMeasurement("proxy_end_to_end", "safe", "ALLOW", 2, 20.0),
            LatencyMeasurement("detector_only", "safe", "ALLOW", 1, 2.0),
        ]
    )

    proxy_all = next(
        row for row in rows
        if row["benchmark"] == "proxy_end_to_end" and row["action"] == "ALL"
    )
    detector_all = next(
        row for row in rows
        if row["benchmark"] == "detector_only" and row["action"] == "ALL"
    )

    assert proxy_all["avg_latency_ms"] == 15.0
    assert proxy_all["avg_response_time_ms"] == 15.0
    assert proxy_all["p95_latency_ms"] == 20.0
    assert detector_all["avg_response_time_ms"] == ""
