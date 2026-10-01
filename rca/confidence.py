"""Evidence-weighted scores are ranking weights, not calibrated probabilities."""


def evidence_weighted_confidence(raw: float) -> float:
    return round(max(0.0, min(1.0, raw)), 3)
