from __future__ import annotations

from typing import Any

from recovery.verifier import RecoveryResult, RecoveryStatus

SYMPTOM_KEYS = ("latency_avg", "packet_loss_pct")


def extract_symptom_metrics(evidence_payloads: list[dict[str, Any]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for item in evidence_payloads:
        metric = item.get("metric")
        value = item.get("value")
        if metric in SYMPTOM_KEYS and isinstance(value, (int, float)):
            metrics[metric] = float(value)
    return metrics


def verify_recovery(
    metrics_before: dict[str, float],
    metrics_after: dict[str, float],
    latency_ok_ms: float = 5.0,
    loss_ok_pct: float = 0.5,
) -> RecoveryResult:
    remaining: list[str] = []
    changed: list[str] = []
    for key in set(metrics_before) | set(metrics_after):
        before = metrics_before.get(key)
        after = metrics_after.get(key)
        if before is not None and after is not None and after != before:
            changed.append(key)
    latency = metrics_after.get("latency_avg")
    loss = metrics_after.get("packet_loss_pct")
    if latency is not None and latency > latency_ok_ms:
        remaining.append(f"latency_avg={latency}ms")
    if loss is not None and loss > loss_ok_pct:
        remaining.append(f"packet_loss_pct={loss}%")
    if not remaining:
        status = RecoveryStatus.VERIFIED
        conclusion = "Symptoms returned to within recovery thresholds relative to healthy operation."
    elif latency is not None and metrics_before.get("latency_avg") is not None and latency < metrics_before["latency_avg"]:
        status = RecoveryStatus.PARTIAL
        conclusion = "Symptoms improved but did not fully return to recovery thresholds."
    elif loss is not None and metrics_before.get("packet_loss_pct") is not None and loss < metrics_before["packet_loss_pct"]:
        status = RecoveryStatus.PARTIAL
        conclusion = "Symptoms improved but did not fully return to recovery thresholds."
    else:
        status = RecoveryStatus.FAILED
        conclusion = "Symptoms remain; investigation should continue. Command success is not recovery."
    return RecoveryResult(
        recovery_status=status,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
        changed_metrics=sorted(changed),
        remaining_symptoms=remaining,
        conclusion=conclusion,
    )
