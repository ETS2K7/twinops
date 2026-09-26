# TwinOps

> **Action-Oriented Autonomous SRE Agent with Digital Twin Sandboxing & Human Approval Gates**
> Built for the **Agents That Act** Hackathon (TrueFoundry × Polaris School of Technology).

---

## Overview

Most AI SRE tools operate in read-only mode: they summarize dashboards and generate alerts, but cannot touch production because deploying unverified LLM-generated code to production carries unacceptable risk.

**TwinOps** bridges the gap between observation and safe autonomous action:
1. **Investigates** live telemetry and APM metrics over Model Context Protocol (FastMCP).
2. **Reproduces** the crash inside an isolated **Digital Twin sandbox** under synthetic load to prove the failure mode.
3. **Verifies** candidate patches under **2x chaos stress testing** to ensure a 0.0% error rate and clean blast radius with zero regressions.
4. **Enforces Human-in-the-Loop Approval** via TrueForge's native tool approval gate before any canary deployment to live production.

---

## Architecture

```
                      +-----------------------------+
                      |       TrueForge UI          |
                      |   (Human Approval Gate)     |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     TwinOps SRE Agent       |
                      |  (gemini-2.5-flash via      |
                      |   Vertex AI OpenAI Proxy)   |
                      +--------------+--------------+
                                     |  MCP over SSE (:8000/sse)
                                     v
                      +-----------------------------+
                      |     TwinOps FastMCP Server  |
                      +--------------+--------------+
                                     |
        +----------------------------+----------------------------+
        |                                                         |
        v                                                         v
+-------------------------------+                       +-------------------------------+
|     Digital Twin Sandbox      |                       |     Target Service (:8001)    |
| - In-memory replica           |                       | - Live FastAPI Checkout API   |
| - Deterministic crash repro   |                       | - DB Connection Pool Leak     |
| - 2x load stress verification |                       | - Real-time APM Telemetry     |
+-------------------------------+                       +-------------------------------+
```

---

## The 4-Step Remediation Protocol

1. **Ingest & Investigate (`fetch_incident_telemetry`)**
   Queries live APM telemetry for incident `INC-893`. Discovers `ConnectionPoolExhaustedError` (100% pool utilization, wait queue backlog) caused by culprit commit `c64b53e` leaving connection unreleased in `target_service/app.py`.

2. **Digital Twin Reproduction & Stress Proof (`run_digital_twin_sandbox`)**
   Spins up an isolated replica environment:
   * **Baseline Crash**: Replays burst traffic, confirming 66.7% error rate under synthetic load.
   * **Surgical Patch Injection**: Applies `finally: pool.release(conn)`.
   * **Chaos Stress Testing**: Replays 30 concurrent requests under 2x load, confirming 0.0% error rate and clean blast radius with 0 regressions.

3. **Human-in-the-Loop Sign-off (`deploy_canary_remediation`)**
   TwinOps formats the complete incident autopsy and unified diff. When it requests deployment, TrueForge pauses execution and presents an interactive approval modal to the engineer.

4. **Production Verification**
   Upon human approval, the canary is deployed to live traffic, restoring production health to 100% HEALTHY.

---

## Quick Start

### 1. Prerequisites
* Python 3.12+
* Node.js 18+ (for TrueForge)
* Google Cloud SDK with Application Default Credentials (ADC)

### 2. Setup
```bash
git clone https://github.com/ETS2K7/twinops.git
cd twinops
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch Services
```bash
# Terminal 1: Target Service (:8001) & FastMCP Server (:8000)
.venv/bin/python -m demo.start_services

# Terminal 2: Vertex AI OpenAI Proxy (:8002)
.venv/bin/python -m vertex_proxy.server

# Terminal 3: TrueForge Daemon (:8790)
NETWORK_POLICY_ENABLED=false npx --yes @truefoundry/trueforge
```

### 4. Configure Agent & Simulate Incident
```bash
# Register model provider and create TwinOps agent in TrueForge
.venv/bin/python -m demo.setup_agent

# Trigger P1 traffic surge outage
.venv/bin/python -m demo.simulate_incident
```

Open `http://localhost:8790`, select the **`twinops`** agent, and send:
```text
🚨 P1 Incident Alert INC-893: The checkout-api is suffering 90%+ errors from DB connection pool exhaustion. Investigate the telemetry, reproduce and verify the fix in the Digital Twin sandbox, and propose canary remediation.
```

---

## Live Benchmark Results

| Metric | Baseline (Unpatched) | Digital Twin Verification (Patched) | Post-Canary Production |
|---|---|---|---|
| **Error Rate** | 66.7% (Pool Exhausted) | **0.0%** (30/30 passed) | **0.0%** |
| **P95 Latency** | Timeout (> 2000ms) | **42ms** | **28ms** |
| **Pool Saturation** | 5 / 5 (100% Starvation) | **1 / 5 (Stable)** | **1 / 5 (Stable)** |
| **Blast Radius** | Severe Outage | **Clean (0 Regressions)** | **Healthy (100%)** |

---

## License
MIT
