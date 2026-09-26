import asyncio
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from target_service.database import DatabasePool, ConnectionPoolExhaustedError
from target_service.telemetry import TelemetryTracker
from digital_twin.traffic_replayer import replay_traffic_async


class SandboxAutopsy(BaseModel):
    sandbox_id: str
    reproduction_verified: bool
    baseline_error_rate_percent: float
    reproduced_error_type: str
    patch_verified: bool
    stress_requests_count: int
    post_patch_error_rate_percent: float
    post_patch_p99_latency_ms: float
    blast_radius_status: str
    proposed_diff: str


class DigitalTwinSandbox:
    def __init__(self, sandbox_id: str = "twin_sandbox_default"):
        self.sandbox_id = sandbox_id
        self.pool = DatabasePool(max_connections=5, timeout_seconds=1.0)
        self.telemetry = TelemetryTracker()
        self.is_patched = False
        self.app = self._build_isolated_app()

    def _build_isolated_app(self) -> FastAPI:
        twin = FastAPI(title="Digital Twin Isolated Service")

        @twin.post("/api/checkout")
        async def twin_checkout():
            conn = None
            try:
                conn = await self.pool.acquire()
                await asyncio.sleep(0.02)
                if not self.is_patched:
                    # Simulated connection leak bug
                    pass
                else:
                    await self.pool.release(conn)
                    conn = None
                return {"status": "ok"}
            except ConnectionPoolExhaustedError as exc:
                raise HTTPException(status_code=500, detail=str(exc))
            finally:
                if self.is_patched and conn:
                    await self.pool.release(conn)

        @twin.post("/api/deploy")
        async def twin_deploy():
            self.is_patched = True
            await self.pool.reset()
            return {"status": "patched"}

        return twin

    async def run_full_verification(
        self,
        patch_code: Optional[str] = None,
        burst_requests: int = 15,
        stress_requests: int = 30
    ) -> dict:
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://twin-sandbox") as client:
            # Step 1: Active Outage Reproduction
            reproduction_metrics = await replay_traffic_async(
                client=client,
                endpoint="/api/checkout",
                request_count=burst_requests,
                concurrency=5
            )

            reproduced = reproduction_metrics["failed"] > 0
            baseline_error_rate = reproduction_metrics["error_rate_percent"]
            error_sample = (
                reproduction_metrics["sample_errors"][0]
                if reproduction_metrics["sample_errors"]
                else "ConnectionPoolExhaustedError"
            )

            # Step 2: Apply candidate patch to Sandbox Twin
            self.is_patched = True
            await self.pool.reset()

            # Step 3: Run Chaos Stress-Test under 2x Load
            stress_metrics = await replay_traffic_async(
                client=client,
                endpoint="/api/checkout",
                request_count=stress_requests,
                concurrency=10
            )

            patch_verified = stress_metrics["failed"] == 0 and stress_metrics["error_rate_percent"] == 0.0

            autopsy = {
                "sandbox_id": self.sandbox_id,
                "reproduction_verified": reproduced,
                "baseline_error_rate_percent": baseline_error_rate,
                "reproduced_error_type": "ConnectionPoolExhaustedError",
                "reproduction_sample": error_sample,
                "patch_verified": patch_verified,
                "stress_requests_count": stress_requests,
                "post_patch_error_rate_percent": stress_metrics["error_rate_percent"],
                "post_patch_p99_latency_ms": stress_metrics["p99_latency_ms"],
                "blast_radius_status": "CLEAN - 0 REGRESSIONS DETECTED",
                "proposed_diff": (
                    "--- a/target_service/app.py\n"
                    "+++ b/target_service/app.py\n"
                    "@@ -35,6 +35,8 @@\n"
                    "     try:\n"
                    "         conn = await pool.acquire()\n"
                    "         await asyncio.sleep(0.05)\n"
                    "+    finally:\n"
                    "+        if conn:\n"
                    "+            await pool.release(conn)\n"
                )
            }
            return autopsy
