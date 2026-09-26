import asyncio
from digital_twin.sandbox import DigitalTwinSandbox


def test_digital_twin_sandbox():
    async def _run():
        sandbox = DigitalTwinSandbox("test_sandbox_01")
        result = await sandbox.run_full_verification(burst_requests=15, stress_requests=30)

        assert result["reproduction_verified"] is True
        assert result["baseline_error_rate_percent"] > 0
        assert "ConnectionPoolExhaustedError" in result["reproduced_error_type"]
        assert result["patch_verified"] is True
        assert result["post_patch_error_rate_percent"] == 0.0
        assert result["stress_requests_count"] == 30
        assert "CLEAN" in result["blast_radius_status"]

        print("Digital Twin Verification Autopsy:")
        print(f"  • Reproduced: {result['reproduction_verified']} (Baseline Error: {result['baseline_error_rate_percent']}%)")
        print(f"  • Patch Verified: {result['patch_verified']} (Post-patch Error: {result['post_patch_error_rate_percent']}%)")
        print(f"  • Stress Requests: {result['stress_requests_count']} sent under 10 concurrent workers")
        print(f"  • Blast Radius: {result['blast_radius_status']}")

    asyncio.run(_run())


if __name__ == "__main__":
    test_digital_twin_sandbox()
    print("All Digital Twin Sandbox tests passed!")
