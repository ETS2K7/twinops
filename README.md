# TwinOps

> **Action-Oriented Autonomous SRE Agent with Digital Twin Sandboxing & Human Approval Gates**
> Built for the **Agents That Act** Hackathon (TrueFoundry × Polaris School of Technology).

---

## 1. The Problem

Most AI SRE tools operate exclusively in read-only observation mode: they summarize dashboards, explain stack traces, and ping Slack channels, but cannot take action. Engineering teams cannot trust unverified LLM-generated code touching production systems at 2 AM without concrete empirical proof that the patch actually works and introduces zero regressions.

**TwinOps** bridges the gap between observation and safe action by introducing a **Digital Twin sandbox** verification loop backed by **TrueForge's native Human-in-the-Loop approval gate**.

---

## 2. What the Agent Reaches & Where It Stops

### What the Agent Reaches
* **Live APM Telemetry & Metrics**: Reaches the target checkout service over Model Context Protocol (FastMCP) to inspect connection pool utilization, wait queues, error stack traces, and culprit git commits.
* **Digital Twin Sandbox Replica**: Reaches an isolated, in-memory replica environment where it mounts a cloned service and database pool to actively reproduce the failure and stress-test candidate code fixes.
* **Production Canary Deployment**: Reaches the production canary deployment endpoint on the target service to apply the verified patch and route initial canary traffic.

### Where It Stops (The Hard Safety Invariant)
* **The Human Approval Checkpoint**: The agent is **strictly prohibited from touching production autonomously**. When TwinOps completes sandbox verification, it formats a comprehensive incident autopsy and unified code diff. It then calls `deploy_canary_remediation`.
* **TrueForge Policy Gate**: TrueForge intercepts this tool call, halts agent execution, and renders an interactive **Human Approval Modal**. The agent cannot proceed until an authenticated human engineer explicitly reviews the autopsy and clicks **Allow**.

---

## 3. System Architecture

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

## 4. How TrueForge Was Used

TrueForge acts as the core agent execution harness and safety control plane:
1. **MCP Tool Integration**: TrueForge connects to the TwinOps FastMCP server via Server-Sent Events (`/sse` on port `8000`), dynamically loading `fetch_incident_telemetry`, `run_digital_twin_sandbox`, and `deploy_canary_remediation`.
2. **Model Gateway**: TrueForge interfaces with Google Cloud Vertex AI (Gemini 2.5 Flash) via a local OpenAI-compatible proxy using Application Default Credentials (ADC).
3. **Safety & Policy Gate**: Configured via the TrueForge SDK (`agent_spec.json` and `setup_agent.py`) with `require_approval_for_tools=['deploy_canary_remediation']`, enforcing cryptographic human sign-off before write actions.
4. **Session Management & Streaming**: TrueForge manages the agent ReAct loop, streaming thoughts, tool requests, and execution events directly to the web UI.

---

## 5. What Is Real vs. What Is Mocked

| Component | Status | Details |
|---|---|---|
| **TrueForge Agent Harness** | **100% Real** | Live TrueForge daemon running on `:8790` handling sessions, MCP tools, and approval modals. |
| **FastMCP Server** | **100% Real** | Live MCP protocol server running on port `8000` over SSE with tool schemas and execution. |
| **LLM Reasoning & Function Calling** | **100% Real** | Live Google Gemini 2.5 Flash on GCP Vertex AI (`us-central1`) via OpenAI proxy with streaming. |
| **Digital Twin Sandbox & Traffic Replayer** | **100% Real** | Active in-memory replica with real async HTTP load generation, real connection pool concurrency, and real error tracking. |
| **Target Service & APM Telemetry** | **100% Real** | Production-like FastAPI checkout service on port `8001` with genuine async concurrency locks and connection exhaustion. |
| **Database Engine** | **Simulated** | In-memory simulated PostgreSQL connection pool (5 max connections, 1s acquisition timeout) modeling leak behavior rather than a physical external RDS/Postgres container to allow instant zero-dependency execution. |

---

## 6. Known Limits

1. **In-Memory State Scope**: The current Digital Twin sandbox clones in-memory state and application connection pools. Clustered state across multiple distributed Kubernetes nodes requires container-level cloning (e.g. Docker-in-Docker or ephemeral namespaces).
2. **Patch Complexity**: TwinOps currently excels at surgical operational fixes (e.g. missing `finally: release()`, timeout adjustments, connection pool resizing). Multi-file structural architecture refactors require human authoring.
3. **Token Context Limits**: Long-running incidents with thousands of log lines require vector or embedding compaction before ingestion into the context window.

---

## 7. The 4-Step Remediation Protocol

1. **Ingest & Investigate (`fetch_incident_telemetry`)**
   Queries live APM telemetry for incident `INC-893`. Discovers `ConnectionPoolExhaustedError` (100% pool utilization, wait queue backlog) caused by culprit commit `c64b53e` leaving connection unreleased in `target_service/app.py`.

2. **Digital Twin Reproduction & Stress Proof (`run_digital_twin_sandbox`)**
   Spins up an isolated replica environment:
   * **Baseline Crash**: Replays burst traffic, confirming **66.7% error rate** under synthetic load.
   * **Surgical Patch Injection**: Applies `finally: pool.release(conn)`.
   * **Chaos Stress Testing**: Replays 30 concurrent requests under 2x load, confirming **0.0% error rate** and clean blast radius with 0 regressions.

3. **Human-in-the-Loop Sign-off (`deploy_canary_remediation`)**
   TwinOps formats the complete incident autopsy and unified diff. When it requests deployment, TrueForge pauses execution and presents an interactive approval modal to the engineer.

4. **Production Verification**
   Upon human approval, the canary is deployed to live traffic, restoring production health to **100% HEALTHY**.

---

## 8. Live Benchmark Results

| Metric | Baseline (Unpatched) | Digital Twin Verification (Patched) | Post-Canary Production |
|---|---|---|---|
| **Error Rate** | 66.7% (Pool Exhausted) | **0.0%** (30/30 passed) | **0.0%** |
| **P95 Latency** | Timeout (> 2000ms) | **42ms** | **28ms** |
| **Pool Saturation** | 5 / 5 (100% Starvation) | **1 / 5 (Stable)** | **1 / 5 (Stable)** |
| **Blast Radius** | Severe Outage | **Clean (0 Regressions)** | **Healthy (100%)** |

---

## 9. Quick Start

### Prerequisites
* Python 3.12+
* Node.js 18+ (for TrueForge)
* Google Cloud SDK with Application Default Credentials (ADC) or API key

### Setup
```bash
git clone https://github.com/ETS2K7/twinops.git
cd twinops
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Launch Services
```bash
# Terminal 1: Target Service (:8001) & FastMCP Server (:8000)
.venv/bin/python -m demo.start_services

# Terminal 2: Vertex AI OpenAI Proxy (:8002)
.venv/bin/python -m vertex_proxy.server

# Terminal 3: TrueForge Daemon (:8790)
NETWORK_POLICY_ENABLED=false npx --yes @truefoundry/trueforge
```

### Configure Agent & Simulate Incident
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

## 10. License
[MIT](LICENSE)
