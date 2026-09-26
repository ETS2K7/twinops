import asyncio
from mcp_server.server import server


def test_mcp_server_tools():
    async def _run():
        # 1. Verify tools registered
        tools = await server.list_tools()
        tool_names = [t.name for t in tools]
        assert "fetch_incident_telemetry" in tool_names
        assert "run_digital_twin_sandbox" in tool_names
        assert "deploy_canary_remediation" in tool_names
        print("MCP Tools Registered:", tool_names)

        # 2. Test fetch_incident_telemetry
        telemetry = await server.call_tool("fetch_incident_telemetry", {"incident_id": "INC-893"})
        assert telemetry is not None
        print("fetch_incident_telemetry verified:", type(telemetry))

        # 3. Test run_digital_twin_sandbox
        sandbox_res = await server.call_tool("run_digital_twin_sandbox", {"patch_code": "pool.release()"})
        assert sandbox_res is not None
        print("run_digital_twin_sandbox verified:", type(sandbox_res))

        # 4. Test deploy_canary_remediation
        deploy_res = await server.call_tool("deploy_canary_remediation", {"patch_id": "patch_pool_001", "canary_weight_percent": 5})
        assert deploy_res is not None
        print("deploy_canary_remediation verified:", type(deploy_res))

    asyncio.run(_run())


if __name__ == "__main__":
    test_mcp_server_tools()
    print("All FastMCP server tool tests passed successfully!")
