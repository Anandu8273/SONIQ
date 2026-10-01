from __future__ import annotations

from datetime import datetime, timezone

from backend.ids import IdFactory
from evidence.models import Evidence, EvidenceType, Significance
from evidence.normalizer import EvidenceNormalizer
from evidence.store import EvidenceStore
from tools.base import ToolResult


def test_evidence_is_observation_not_conclusion() -> None:
    evidence = Evidence(
        evidence_id="EVID-001",
        timestamp=datetime.now(timezone.utc),
        node="leaf1",
        interface="Ethernet0",
        evidence_type=EvidenceType.INTERFACE_COUNTER,
        metric="rx_errors",
        value=124,
        unit="count",
        baseline=0,
        source="sonic_cli",
        tool="get_interface_errors",
        significance=Significance.ELEVATED,
    )
    dumped = evidence.model_dump()
    assert dumped["value"] == 124
    assert dumped["baseline"] == 0
    assert "broken" not in str(dumped).lower()


def test_store_roundtrip() -> None:
    store = EvidenceStore()
    evidence = Evidence(
        evidence_id="EVID-001",
        timestamp=datetime.now(timezone.utc),
        node="leaf1",
        evidence_type=EvidenceType.LATENCY,
        metric="latency_avg",
        value=35.0,
        unit="ms",
        source="mock",
        tool="get_latency",
        investigation_id="INV-001",
    )
    store.add(evidence)
    assert store.get("EVID-001") is evidence
    assert len(store.list("INV-001")) == 1


def test_normalize_latency() -> None:
    normalizer = EvidenceNormalizer(IdFactory())
    result = ToolResult(
        tool="get_latency",
        status="OK",
        node="leaf1",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        success=True,
        data={
            "status": "OK",
            "node": "leaf1",
            "destination": "leaf2",
            "min_ms": 30.0,
            "avg_ms": 35.0,
            "max_ms": 42.0,
            "packet_count": 5,
            "baseline_avg_ms": 2.0,
        },
    )
    items = normalizer.normalize(result, "INV-001")
    assert len(items) == 1
    assert items[0].metric == "latency_avg"
    assert items[0].value == 35.0
    assert items[0].significance == Significance.ELEVATED


def test_unavailable_is_not_zero() -> None:
    normalizer = EvidenceNormalizer(IdFactory())
    result = ToolResult(
        tool="get_bgp_status",
        status="unsupported_or_unavailable",
        node="leaf1",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        success=False,
        error="BGP is not configured on this virtual SONiC node",
        data={
            "status": "unsupported_or_unavailable",
            "reason": "BGP is not configured on this virtual SONiC node",
            "node": "leaf1",
        },
    )
    items = normalizer.normalize(result, "INV-001")
    assert items[0].significance == Significance.UNAVAILABLE
    assert items[0].value != 0
    assert items[0].confidence == "unavailable"
