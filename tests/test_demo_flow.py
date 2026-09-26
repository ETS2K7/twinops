import asyncio
import httpx
from target_service.app import app as target_app
from digital_twin.sandbox import DigitalTwinSandbox
from mcp_server.tools import fetch_telemetry_impl, run_sandbox_impl, deploy_canary_impl


def test_full_demo_simulation_cycle():
    async def _run():
        transport = httpx.ASGITransport(app=target_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://target-api") as client:
            # 1. Reset
            await client.post("/api/reset")

            # 2. Fire burst traffic to trigger outage
            for i in range(10):
                await client.post("/api/checkout", json={"cart_id": f"burst_{i}", "amount": 99.0})

            # 3. Verify P1 incident recorded
            incident_resp = await client.get("/api/incident")
            assert incident_resp.status_code == 200
            incident = incident_resp.json()
            assert incident is not None
            assert incident["error_type"] == "ConnectionPoolExhaustedError"
            print("Demo Flow: P1 Outage triggered successfully (Incident ID:", incident["incident_id"], ")")

            # 4. Agent Tool 1: Fetch Telemetry
            telemetry = await fetch_telemetry_impl(incident["incident_id"], target_url="http://target-api")
            assert telemetry is not None
            print("Demo Flow: Telemetry fetched:", telemetry["error_type"])

            # 5. Agent Tool 2: Digital Twin Sandbox
            sandbox_res = await run_sandbox_impl()
            assert sandbox_res["reproduction_verified"] is True
            assert sandbox_res["patch_verified"] is True
            assert sandbox_res["post_patch_error_rate_percent"] == 0.0
            print("Demo Flow: Digital Twin Sandbox verified (Post-patch errors: 0.0%)")

            # 6. Agent Tool 3: Deploy Canary
            deploy_res = await client.post("/api/deploy", json={"patch_id": "patch_pool_fix_001", "canary_weight_percent": 5})
            assert deploy_res.status_code == 200
            assert deploy_res.json()["status"] == "canary_deployed"

            # 7. Verify post-deploy production recovery
            for i in range(15):
                resp = await client.post("/api/checkout", json={"cart_id": f"healthy_{i}", "amount": 99.0})
                assert resp.status_code == 200

            health_resp = await client.get("/health")
            assert health_resp.json()["status"] == "healthy"
            print("Demo Flow: Full end-to-end recovery verified. All post-canary requests succeeded!")

    asyncio.run(_run())


if __name__ == "__main__":
    test_full_demo_simulation_cycle()
    print("All demo flow tests passed!")
