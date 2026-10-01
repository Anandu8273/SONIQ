from __future__ import annotations

from recovery.baseline import verify_recovery
from recovery.verifier import RecoveryStatus


def test_recovery_verified() -> None:
    result = verify_recovery(
        {"latency_avg": 35.0, "packet_loss_pct": 20.0},
        {"latency_avg": 2.0, "packet_loss_pct": 0.0},
    )
    assert result.recovery_status == RecoveryStatus.VERIFIED
    assert not result.remaining_symptoms


def test_recovery_partial() -> None:
    result = verify_recovery(
        {"latency_avg": 35.0, "packet_loss_pct": 20.0},
        {"latency_avg": 20.0, "packet_loss_pct": 5.0},
    )
    assert result.recovery_status == RecoveryStatus.PARTIAL


def test_recovery_failed() -> None:
    result = verify_recovery(
        {"latency_avg": 35.0, "packet_loss_pct": 20.0},
        {"latency_avg": 40.0, "packet_loss_pct": 22.0},
    )
    assert result.recovery_status == RecoveryStatus.FAILED
    assert result.remaining_symptoms
