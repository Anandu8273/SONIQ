from __future__ import annotations

from evaluation.evaluator import evaluate_rca
from pathlib import Path
import json


def test_ground_truth_hidden_from_agent_package() -> None:
    path = Path(__file__).resolve().parents[1] / "evaluation" / "ground_truth.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["fault"] == "packet_loss"
    assert "incident" not in data[0]


def test_evaluator_top_match() -> None:
    gt = {"fault": "interface_degradation", "expected_hypotheses": ["interface_degradation"]}
    result = evaluate_rca(gt, "interface_degradation", ["packet_loss", "routing_problem"])
    assert result["rca_match"] is True
    assert result["top3"] is True
