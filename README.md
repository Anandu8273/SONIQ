# SONIQ — Evidence-Driven AI Network Investigator for SONiC

SONIQ is an investigation layer **above** SONiC. It does not guess a root cause. It collects evidence through registered diagnostic tools, updates competing hypotheses, then produces an explainable probable RCA with observed facts separated from inference.

Human approval is required before any potentially disruptive action. The MVP does not change SONiC configuration.

## Current phase (1–5)

Working now:

1. Repository structure
2. Pydantic models
3. Tool registry (read-only tools only)
4. Mock diagnostic tools with deterministic fixtures
5. Investigation loop **without an LLM** (deterministic planner)

Not in this phase: live SONiC CLI execution in tests, LLM tool calling, React dashboard, autonomous remediation.

## First demonstration

From the repository root (`d:\PROJECT\SONIQ`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests -q
python backend/demo.py
```

What the demo does:

- Creates incident `High latency between Leaf-1 and Leaf-2`
- Seeds seven connectivity hypotheses
- Calls mock tools (`get_latency`, `get_packet_loss`, `get_interface_errors`, …)
- Stores structured evidence
- Updates hypotheses with explicit rules
- Prints an RCA-ready report (facts vs inference) with **APPROVAL REQUIRED**

Expected mock observations for this scenario:

- Latency ~35 ms vs baseline 2 ms
- Packet loss 0%
- Interface errors 0
- Route installed
- BGP established
- ASIC/platform: unavailable (not fabricated)

The planner should weaken interface/routing/BGP/loss hypotheses and treat elevated latency as a congestion/path-delay hypothesis **without claiming certainty**.

Optional second scenario:

```powershell
python backend/demo.py --scenario interface_degradation_leaf1
```

## Tests

```powershell
python -m pytest tests -q
```

Tests use mocked SONiC responses. A live topology is not required.

## Configuration

Edit `config/config.yaml`. Node container names are **not** hard-coded in Python. Do not put passwords or API keys in this file.

```yaml
sonic:
  nodes:
    leaf1:
      transport: docker
      container: sonic-leaf1
    leaf2:
      transport: docker
      container: sonic-leaf2
tools:
  mode: mock
  allow_write: false
agent:
  max_steps: 10
  require_approval: true
  llm_enabled: false
```

## Replacing mocks with real SONiC (next phase)

Do **not** change the existing topology.

The agent calls tools by name (`get_interface_errors`). Tools call `NetworkAdapter` methods. Swap `MockSonicAdapter` for `SONiCCLIAdapter` when you are ready:

- Interface: `adapters/base.py` (`execute`, `get_interface_stats`, `get_interface_errors`, `get_latency`, `get_packet_loss`, `get_routes`, `get_bgp_status`, `get_logs`, `get_config`, `get_asic_state`, `get_platform_health`)
- Live CLI: `adapters/sonic_cli.py` (docker exec or later SSH; command strings come from `config.yaml`)
- gNMI: `adapters/gnmi.py` stub for later Get/Subscribe

Before enabling live commands, confirm each CLI exists on your SONiC image. If a command is missing, change the template in config; do not assume a command.

Set `tools.mode: live` only after those commands are verified. Read-only investigation remains the default.

## API (thin)

```powershell
uvicorn backend.main:app --reload
```

Endpoints include `POST /incidents`, `POST /incidents/{id}/investigate`, evidence/hypotheses/report, `POST .../approve`, `POST .../verify`.

## Design rules

- The LLM (when added) may only emit `CALL_TOOL`, `FINALIZE_RCA`, or `REQUEST_HUMAN_APPROVAL`.
- Network facts come from tools. Unavailable ≠ observed zero.
- Confidence is **evidence-weighted**, not a calibrated probability.
- Ground truth in `evaluation/ground_truth.json` is for scoring only. The agent never reads it.
