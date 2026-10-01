"""Offline evaluation. Ground truth is never passed to the investigation agent."""

from __future__ import annotations

from typing import Any


def evaluate_rca(ground_truth: dict[str, Any], probable_key: str, alternative_keys: list[str]) -> dict[str, Any]:
    expected = ground_truth.get("expected_hypotheses") or [ground_truth.get("fault")]
    top3 = [probable_key, *alternative_keys][:3]
    return {
        "rca_match": probable_key in expected,
        "top3": any(item in expected for item in top3),
        "probable_key": probable_key,
        "expected": expected,
    }
