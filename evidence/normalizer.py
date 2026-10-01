"""Turn tool payloads into Evidence observations. No conclusions are added here."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.ids import IdFactory
from evidence.models import Evidence, EvidenceType, Significance
from tools.base import ToolResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _compare(value: float | int | None, baseline: float | int | None) -> Significance:
    if value is None or baseline is None:
        return Significance.UNKNOWN
    if value > baseline:
        return Significance.ELEVATED
    if value < baseline:
        return Significance.REDUCED
    return Significance.NORMAL


class EvidenceNormalizer:
    def __init__(self, ids: IdFactory) -> None:
        self.ids = ids

    def normalize(self, result: ToolResult, investigation_id: str) -> list[Evidence]:
        if result.status in {"TIMEOUT", "UNAVAILABLE"} or not result.success:
            return [
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=result.node,
                    evidence_type=EvidenceType.AVAILABILITY,
                    metric="tool_availability",
                    value=result.status,
                    source=result.tool,
                    tool=result.tool,
                    significance=Significance.UNAVAILABLE,
                    confidence="unavailable",
                    investigation_id=investigation_id,
                    notes=result.error or result.data.get("reason"),
                )
            ]
        tool = result.tool
        data = result.data
        if tool == "get_interface_stats":
            return self._iface_stats(data, investigation_id)
        if tool == "get_interface_errors":
            return self._iface_errors(data, investigation_id)
        if tool == "get_latency":
            return self._latency(data, investigation_id)
        if tool == "get_packet_loss":
            return self._packet_loss(data, investigation_id)
        if tool == "get_route":
            return self._routes(data, investigation_id)
        if tool == "get_bgp_status":
            return self._bgp(data, investigation_id)
        if tool == "get_logs":
            return self._logs(data, investigation_id)
        if tool == "get_config":
            return self._config(data, investigation_id)
        if tool == "get_asic_state":
            return self._unavailable_kind(data, investigation_id, EvidenceType.ASIC, "asic_state", "get_asic_state")
        if tool == "get_platform_health":
            return self._platform(data, investigation_id)
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=result.node,
                evidence_type=EvidenceType.AVAILABILITY,
                metric="unparsed_tool_output",
                value=None,
                source=tool,
                tool=tool,
                significance=Significance.UNKNOWN,
                investigation_id=investigation_id,
                notes="Tool returned data without a dedicated normalizer; stored as availability notice only.",
            )
        ]

    def _iface_stats(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        items: list[Evidence] = []
        for row in data.get("interfaces", []):
            iface = row.get("interface")
            node = data.get("node")
            items.append(
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=node,
                    interface=iface,
                    evidence_type=EvidenceType.INTERFACE_STATUS,
                    metric="oper_status",
                    value=row.get("oper_status"),
                    source="mock" if "raw" not in data else "sonic_cli",
                    tool="get_interface_stats",
                    significance=Significance.NORMAL if row.get("oper_status") == "up" else Significance.ELEVATED,
                    investigation_id=investigation_id,
                )
            )
            for metric in ("rx_packets", "tx_packets", "rx_bytes", "tx_bytes"):
                items.append(
                    Evidence(
                        evidence_id=self.ids.next("EVID"),
                        timestamp=_now(),
                        node=node,
                        interface=iface,
                        evidence_type=EvidenceType.INTERFACE_COUNTER,
                        metric=metric,
                        value=row.get(metric),
                        unit="count" if "packets" in metric else "bytes",
                        source="mock",
                        tool="get_interface_stats",
                        significance=Significance.UNKNOWN,
                        investigation_id=investigation_id,
                    )
                )
        return items

    def _iface_errors(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        items: list[Evidence] = []
        for row in data.get("interfaces", []):
            node = data.get("node")
            iface = row.get("interface")
            for metric in ("rx_errors", "tx_errors", "crc_errors", "drops", "discards"):
                value = row.get(metric)
                baseline = row.get(f"baseline_{metric}")
                items.append(
                    Evidence(
                        evidence_id=self.ids.next("EVID"),
                        timestamp=_now(),
                        node=node,
                        interface=iface,
                        evidence_type=EvidenceType.INTERFACE_COUNTER,
                        metric=metric,
                        value=value,
                        unit="count",
                        baseline=baseline,
                        deviation=None if value is None or baseline is None else float(value) - float(baseline),
                        source="mock",
                        tool="get_interface_errors",
                        significance=_compare(value, baseline),
                        investigation_id=investigation_id,
                    )
                )
        return items

    def _latency(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        avg = data.get("avg_ms")
        baseline = data.get("baseline_avg_ms")
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=EvidenceType.LATENCY,
                metric="latency_avg",
                value=avg,
                unit="ms",
                baseline=baseline,
                deviation=None if avg is None or baseline is None else float(avg) - float(baseline),
                source="mock",
                tool="get_latency",
                significance=_compare(avg, baseline),
                investigation_id=investigation_id,
                notes=f"destination={data.get('destination')} min={data.get('min_ms')} max={data.get('max_ms')} n={data.get('packet_count')}",
            )
        ]

    def _packet_loss(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        loss = data.get("loss_percentage")
        baseline = data.get("baseline_loss_percentage")
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=EvidenceType.PACKET_LOSS,
                metric="packet_loss_pct",
                value=loss,
                unit="percent",
                baseline=baseline,
                deviation=None if loss is None or baseline is None else float(loss) - float(baseline),
                source="mock",
                tool="get_packet_loss",
                significance=_compare(loss, baseline),
                investigation_id=investigation_id,
                notes=(
                    f"tx={data.get('packets_transmitted')} rx={data.get('packets_received')} dest={data.get('destination')}"
                ),
            )
        ]

    def _routes(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        routes = data.get("routes") or []
        if not routes:
            return [
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=data.get("node"),
                    evidence_type=EvidenceType.ROUTE,
                    metric="route_present",
                    value=False,
                    source="mock",
                    tool="get_route",
                    significance=Significance.ELEVATED,
                    investigation_id=investigation_id,
                    notes="No matching route returned.",
                )
            ]
        items: list[Evidence] = []
        for route in routes:
            items.append(
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=data.get("node"),
                    interface=route.get("interface"),
                    evidence_type=EvidenceType.ROUTE,
                    metric="route_state",
                    value=route.get("route_state"),
                    source="mock",
                    tool="get_route",
                    significance=Significance.NORMAL if route.get("route_state") == "installed" else Significance.ELEVATED,
                    investigation_id=investigation_id,
                    notes=(
                        f"prefix={route.get('prefix')} next_hop={route.get('next_hop')} "
                        f"protocol={route.get('protocol')} destination={route.get('destination')}"
                    ),
                )
            )
        return items

    def _bgp(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        if data.get("status") in {"unsupported_or_unavailable", "UNAVAILABLE"}:
            return [
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=data.get("node"),
                    evidence_type=EvidenceType.BGP,
                    metric="bgp_availability",
                    value="unsupported_or_unavailable",
                    source="mock",
                    tool="get_bgp_status",
                    significance=Significance.UNAVAILABLE,
                    confidence="unavailable",
                    investigation_id=investigation_id,
                    notes=data.get("reason") or "BGP is not configured on this virtual SONiC node",
                )
            ]
        items: list[Evidence] = []
        for neighbor in data.get("neighbors", []):
            state = neighbor.get("session_state")
            items.append(
                Evidence(
                    evidence_id=self.ids.next("EVID"),
                    timestamp=_now(),
                    node=data.get("node"),
                    evidence_type=EvidenceType.BGP,
                    metric="bgp_session_state",
                    value=state,
                    source="mock",
                    tool="get_bgp_status",
                    significance=Significance.NORMAL if state == "established" else Significance.ELEVATED,
                    investigation_id=investigation_id,
                    notes=(
                        f"neighbor={neighbor.get('neighbor')} remote_as={neighbor.get('remote_as')} "
                        f"local_as={neighbor.get('local_as')} uptime={neighbor.get('uptime')} "
                        f"rx_prefixes={neighbor.get('prefixes_received')} "
                        f"tx_prefixes={neighbor.get('prefixes_advertised')}"
                    ),
                )
            )
        return items

    def _logs(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=EvidenceType.LOG,
                metric="log_summary",
                value=data.get("summary"),
                source="mock",
                tool="get_logs",
                significance=Significance.UNKNOWN,
                investigation_id=investigation_id,
                notes=f"lines={len(data.get('lines') or [])} truncated={data.get('truncated')}",
            )
        ]

    def _config(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=EvidenceType.CONFIG,
                metric="config_snapshot",
                value=data.get("config"),
                source="mock",
                tool="get_config",
                significance=Significance.UNKNOWN,
                investigation_id=investigation_id,
                notes="Read-only configuration snapshot.",
            )
        ]

    def _platform(self, data: dict[str, Any], investigation_id: str) -> list[Evidence]:
        if data.get("status") != "OK":
            return self._unavailable_kind(data, investigation_id, EvidenceType.PLATFORM, "platform_health", "get_platform_health")
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=EvidenceType.PLATFORM,
                metric="platform_health",
                value=data,
                source="mock",
                tool="get_platform_health",
                significance=Significance.UNKNOWN,
                investigation_id=investigation_id,
            )
        ]

    def _unavailable_kind(
        self,
        data: dict[str, Any],
        investigation_id: str,
        evidence_type: EvidenceType,
        metric: str,
        tool: str,
    ) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=self.ids.next("EVID"),
                timestamp=_now(),
                node=data.get("node"),
                evidence_type=evidence_type,
                metric=metric,
                value=data.get("status", "UNAVAILABLE"),
                source="mock",
                tool=tool,
                significance=Significance.UNAVAILABLE,
                confidence="unavailable",
                investigation_id=investigation_id,
                notes=data.get("reason") or "not_available_in_current_environment",
            )
        ]
