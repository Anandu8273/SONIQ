# SONIQ

**Evidence-Driven AI Network Investigator for SONiC**

SONIQ is an AI-assisted network operations agent designed to observe a SONiC environment, investigate network issues using real diagnostic evidence, explain likely root causes, and support policy-controlled remediation.

> **Core principle: Evidence Before Action.** Measurements and conclusions must be grounded in collected network evidence. The reasoning model must not invent telemetry or execute arbitrary shell commands.

## Goals

- Connect to real SONiC devices and collect operational data.
- Investigate latency, packet loss, interface errors, routing changes, and BGP failures.
- Select diagnostic tools based on current evidence.
- Maintain investigation state and test competing hypotheses.
- Produce traceable root-cause analysis (RCA).
- Require approval for network-changing actions unless an explicit policy permits them.
- Verify network health after approved remediation.

## Architecture

```text
SONiC Environment
       |
       v
Network Adapter
       |
       v
Registered Diagnostic Tools
       |
       v
Evidence Normalization and Store
       |
       v
Agent State and Hypotheses
       |
       v
Investigation Planner / Reasoner
       |
       +----> Select next tool ----> Collect more evidence
       |
       v
RCA and Recommendation
       |
       v
Approval / Policy Check
       |
       v
Remediation (when implemented and authorized)
       |
       v
Recovery Verification
```

## Repository Structure

```text
SONIQ/
├── adapters/       # SONiC and network transports
├── agent/          # Runtime, decisions, planning, and state
├── backend/        # Configuration and shared utilities
├── config/         # Runtime configuration
├── evidence/       # Evidence models, normalization, and storage
├── rca/            # Root-cause analysis and reporting
├── recovery/       # Baselines and recovery verification
├── tests/          # Automated checks
├── tools/          # Registered diagnostic capabilities
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

The structure may change as real-device integration is implemented.

## Environment

The development lab uses SONiC Virtual Switch (VS) nodes managed with Containerlab. The current lab has two communicating leaf nodes.

SONIQ is intended to run separately and access the nodes through a configured adapter. Normal SONIQ setup should not rebuild or alter the existing SONiC lab.

## Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/Anandu8273/SONIQ.git
   cd SONIQ
   ```

2. Create and activate a Python virtual environment.

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the real SONiC connection using the project's adapter and configuration settings. Keep credentials in environment variables or a local, untracked `.env` file. Never commit secrets.

5. Review the adapter configuration and available tools before running an investigation.

> The launch command and required settings depend on the current implementation. Confirm them in the code and configuration before running against a device.

## Safety

- Use read-only diagnostic access by default.
- Allow the agent to call only registered tools with validated arguments.
- Never pass LLM-generated shell commands directly to a device.
- Require approval and policy checks for configuration changes, restarts, and other write operations.
- Treat failed or unavailable telemetry as unknown, not as proof of health.
- Keep evidence, timestamps, source tools, and decisions traceable.

## Development Status

SONIQ is under active development. Its target workflow is:

**Observe → Reason → Select Tool → Collect Evidence → Update State → Decide → Verify**

A capability should be considered implemented only after it has been verified against the configured SONiC environment. Simulated data must not be presented as real network evidence.

## Contributing

Use feature branches and pull requests. Keep commits focused and review changes before merging. Do not commit credentials, device secrets, generated artifacts, or local environment files.

## License

No license has been added yet. Until one is selected, do not assume the repository grants permission to reuse or redistribute its code.
