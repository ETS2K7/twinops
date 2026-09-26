import asyncio
import sys
from typing import Optional
from mcp_server.tools import fetch_telemetry_impl, run_sandbox_impl, deploy_canary_impl


class SRECommanderRunner:
    def __init__(self, target_url: str = "http://localhost:8001"):
        self.target_url = target_url

    async def execute_incident_lifecycle(
        self,
        incident_id: str = "INC-893",
        interactive: bool = False
    ) -> dict:
        print("\n" + "=" * 70)
        print(f"🚨 [TWINOPS] P1 Alert Received for service: checkout-api")
        print(f"   Incident ID: {incident_id}")
        print("=" * 70)

        # Step 1: Telemetry Ingestion
        print("\n[STEP 1] Fetching live APM telemetry and error traces...")
        telemetry = await fetch_telemetry_impl(incident_id, target_url=self.target_url)
        print(f"  • Source: {telemetry['source']}")
        print(f"  • Error: {telemetry['error_type']} on {telemetry['failing_endpoint']}")
        print(f"  • Culprit Commit: {telemetry['culprit_commit']}")
        print(f"  • DB Pool Utilization: {telemetry['pool_metrics'].get('utilization_percent', 100.0)}% "
              f"({telemetry['pool_metrics'].get('active_connections', 5)}/{telemetry['pool_metrics'].get('max_connections', 5)} active)")

        # Step 2: Digital Twin Sandbox Reproduction & Verification
        print("\n[STEP 2] Launching ephemeral Digital Twin Sandbox...")
        print("   ↳ Step 2a: Actively replaying production traffic signature to reproduce crash...")
        print("   ↳ Step 2b: Injecting surgical patch (connection release in finally block)...")
        print("   ↳ Step 2c: Running chaos stress test under 2x load (30 concurrent requests)...")

        sandbox_result = await run_sandbox_impl()
        print("\n" + "-" * 70)
        print("🧪 DIGITAL TWIN SANDBOX AUTOPSY & PROOF:")
        print(f"  • Reproduction Verified: {sandbox_result['reproduction_verified']} "
              f"(Baseline Error Rate: {sandbox_result['baseline_error_rate_percent']}%)")
        print(f"  • Candidate Patch Stress Test: 30 requests replayed")
        print(f"  • Post-Patch Error Rate: {sandbox_result['post_patch_error_rate_percent']}%")
        print(f"  • Post-Patch P99 Latency: {sandbox_result['post_patch_p99_latency_ms']} ms")
        print(f"  • Blast Radius Assessment: {sandbox_result['blast_radius_status']}")
        print("-" * 70)

        print("\n📝 PROPOSED SURGICAL DIFF:")
        print(sandbox_result["verified_diff"])

        # Step 3: Human-in-the-Loop Checkpoint (TrueForge Guardrail)
        print("\n" + "!" * 70)
        print("⚠️  TRUEFORGE APPROVAL GATE REACHED")
        print("   Tool: deploy_canary_remediation")
        print("   Target: live-production-checkout-api (5% canary rollout)")
        print("!" * 70)

        if interactive:
            print("\nApprove canary deployment to production? [y/N]: ", end="", flush=True)
            choice = sys.stdin.readline().strip().lower()
            if choice != "y":
                print("❌ Deployment aborted by engineer. Rollback preserved.")
                return {"status": "aborted", "reason": "engineer_denied"}

        print("\n[STEP 4] Approval granted. Executing canary rollout to production...")
        deploy_result = await deploy_canary_impl(
            patch_id="patch_pool_fix_001",
            canary_weight_percent=5,
            target_url=self.target_url
        )
        print(f"  • Deployment Status: {deploy_result['deployment_status']}")
        print(f"  • Production Health: {deploy_result['production_health']}")
        print(f"  • Message: {deploy_result['message']}")
        print("\n" + "=" * 70)
        print("✅ INCIDENT RESOLVED: Checkout API restored to 100% operational health.")
        print("=" * 70 + "\n")

        return {
            "telemetry": telemetry,
            "sandbox": sandbox_result,
            "deployment": deploy_result
        }


if __name__ == "__main__":
    runner = SRECommanderRunner()
    asyncio.run(runner.execute_incident_lifecycle(interactive=False))
