"""CLI demonstration of the Phase 1-5 investigation loop (no LLM)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import build_engine
from backend.logging_setup import configure_logging


async def run_demo(scenario: str) -> int:
    configure_logging(level="INFO", json_logs=True)
    engine = build_engine(scenario)
    incident = engine.create_incident(
        title="High latency between Leaf-1 and Leaf-2",
        description="Traffic between Leaf-1 and Leaf-2 is experiencing increased latency",
        source="manual",
        affected_nodes=["leaf1", "leaf2"],
        affected_interfaces=["Ethernet0"],
        source_endpoint="leaf1",
        destination_endpoint="leaf2",
        severity="medium",
    )
    investigation = await engine.investigate(incident)
    print(engine.report_text(investigation))
    print("\n--- investigation json ---")
    print(
        json.dumps(
            {
                "investigation_id": investigation.investigation_id,
                "status": investigation.status.value,
                "steps_taken": investigation.steps_taken,
                "tools": investigation.tool_calls,
                "hypotheses": [
                    {
                        "title": h.title,
                        "status": h.status.value,
                        "confidence": h.confidence,
                        "confidence_type": h.confidence_type,
                    }
                    for h in investigation.hypotheses
                ],
            },
            indent=2,
        )
    )
    return 0 if investigation.rca else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a SONIQ mock investigation (no LLM).")
    parser.add_argument("--scenario", default="high_latency_leaf1_leaf2")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_demo(args.scenario)))


if __name__ == "__main__":
    main()
