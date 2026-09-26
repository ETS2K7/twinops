import asyncio
import time
import httpx


async def simulate_outage(target_url: str = "http://localhost:8001"):
    print("=" * 70)
    print("⚡ [TWINOPS DEMO] Simulating Live Production Traffic Surge...")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=4.0) as client:
        # Reset baseline
        try:
            await client.post(f"{target_url}/api/reset")
        except Exception:
            print(f"⚠️ Target service at {target_url} not reachable. Start services with: python -m demo.start_services")
            return

        print("\n[1] Firing burst traffic (15 concurrent checkout requests)...")
        tasks = []
        for i in range(15):
            payload = {
                "cart_id": f"burst_cart_{i}_{int(time.time())}",
                "user_id": f"customer_{i}",
                "amount": 89.50
            }
            tasks.append(client.post(f"{target_url}/api/checkout", json=payload))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
        failed = len(responses) - success
        error_rate = round((failed / len(responses)) * 100, 1)

        print(f"\n[2] Traffic Burst Completed:")
        print(f"    • Total Requests: {len(responses)}")
        print(f"    • Succeeded:      {success}")
        print(f"    • Failed (500s):   {failed}")
        print(f"    • Error Rate:     {error_rate}%")

        # Fetch incident telemetry
        incident_resp = await client.get(f"{target_url}/api/incident")
        incident = incident_resp.json() if incident_resp.status_code == 200 else {}

        print("\n" + "!" * 70)
        print("🚨 P1 CRITICAL OUTAGE TRIGGERED")
        print("!" * 70)
        print(f"  • Incident ID:       {incident.get('incident_id', 'INC-893')}")
        print(f"  • Service:           {incident.get('service', 'checkout-api')}")
        print(f"  • Error Type:        {incident.get('error_type', 'ConnectionPoolExhaustedError')}")
        print(f"  • DB Pool Saturated: {incident.get('pool_metrics', {}).get('active_connections', 5)}/"
              f"{incident.get('pool_metrics', {}).get('max_connections', 5)} connections locked")
        print(f"  • Culprit Commit:    {incident.get('culprit_commit', 'a4b9c1e: feat(checkout): validate locks')}")

        print("\n" + "=" * 70)
        print("📋 COPY THIS PROMPT INTO TRUEFORGE CHAT (http://localhost:8790):")
        print("=" * 70)
        print(
            f"🚨 P1 Incident Alert {incident.get('incident_id', 'INC-893')}: "
            f"The checkout-api is suffering 90%+ errors from DB connection pool exhaustion. "
            f"Investigate the telemetry, reproduce and verify the fix in the Digital Twin sandbox, "
            f"and propose canary remediation."
        )
        print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(simulate_outage())
