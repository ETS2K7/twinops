import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp_server.tools import fetch_telemetry_impl, run_sandbox_impl, deploy_canary_impl

server = MCPServer(
    name="twinops",
    instructions=(
        "TwinOps SRE tools for autonomous incident remediation. "
        "Use fetch_incident_telemetry to diagnose active outages, "
        "run_digital_twin_sandbox to actively reproduce the failure and stress-test candidate patches, "
        "and deploy_canary_remediation to apply the verified fix to live production with human sign-off."
    )
)


@server.tool(
    name="fetch_incident_telemetry",
    description=(
        "Fetches real-time APM telemetry, error logs, database pool saturation metrics, "
        "stack traces, and culprit commit diff for an active incident on checkout-api."
    )
)
async def fetch_incident_telemetry(incident_id: str) -> dict:
    return await fetch_telemetry_impl(incident_id=incident_id)


@server.tool(
    name="run_digital_twin_sandbox",
    description=(
        "Spins up an ephemeral Digital Twin sandbox replica of the failing service. "
        "Actively replays synthetic production traffic to reproduce the crash (100% reproduction proof), "
        "injects the candidate patch, and stress-tests it under 2x load to verify 0% error rate "
        "and clean blast radius before touching production."
    )
)
async def run_digital_twin_sandbox(patch_code: str = "") -> dict:
    return await run_sandbox_impl(patch_code=patch_code)


@server.tool(
    name="deploy_canary_remediation",
    description=(
        "[CRITICAL - REQUIRES HUMAN APPROVAL] Deploys the sandbox-verified remediation patch "
        "to live production using a scoped canary rollout (default 5% traffic), "
        "resets saturated connection pools, and verifies live production recovery."
    )
)
async def deploy_canary_remediation(patch_id: str, canary_weight_percent: int = 5) -> dict:
    return await deploy_canary_impl(patch_id=patch_id, canary_weight_percent=canary_weight_percent)


app = server.sse_app()

if __name__ == "__main__":
    uvicorn.run("mcp_server.server:app", host="0.0.0.0", port=8000, reload=False)
