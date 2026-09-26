import asyncio
import time
import traceback
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from target_service.database import DatabasePool, ConnectionPoolExhaustedError
from target_service.telemetry import TelemetryTracker

app = FastAPI(title="Production Checkout API", version="1.0.0")

pool = DatabasePool(max_connections=5, timeout_seconds=1.0)
telemetry = TelemetryTracker()
is_patched = False


class CheckoutRequest(BaseModel):
    cart_id: str = Field(default="cart_default")
    user_id: str = Field(default="usr_123")
    amount: float = Field(default=99.0)


class DeployRequest(BaseModel):
    patch_id: str
    patch_code: Optional[str] = None
    canary_weight_percent: int = 5


@app.post("/api/checkout")
async def checkout(request: CheckoutRequest):
    global is_patched
    start_time = time.time()
    conn = None

    try:
        conn = await pool.acquire()
        await asyncio.sleep(0.05)

        if not is_patched:
            # Bug: Connection leak introduced in recent commit; unreleased on normal exit path.
            pass
        else:
            await pool.release(conn)
            conn = None

        duration_ms = (time.time() - start_time) * 1000
        telemetry.record_request(status_code=200, duration_ms=duration_ms, pool_metrics=pool.stats())
        return {
            "status": "success",
            "order_id": f"ord_{request.cart_id[:6]}",
            "amount": request.amount,
            "latency_ms": round(duration_ms, 2)
        }

    except ConnectionPoolExhaustedError as exc:
        duration_ms = (time.time() - start_time) * 1000
        stack = traceback.format_exc()
        telemetry.record_request(
            status_code=500,
            duration_ms=duration_ms,
            error_message=str(exc),
            stack_trace=stack,
            pool_metrics=pool.stats()
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConnectionPoolExhaustedError",
                "message": str(exc),
                "pool_stats": pool.stats()
            }
        )
    finally:
        if is_patched and conn:
            await pool.release(conn)


@app.get("/health")
async def health():
    return {
        "status": "degraded" if pool.active_count >= pool.max_connections else "healthy",
        "is_patched": is_patched,
        "pool": pool.stats(),
        "telemetry": telemetry.metrics_summary()
    }


@app.get("/metrics")
async def metrics():
    return telemetry.metrics_summary()


@app.get("/api/incident")
async def get_incident():
    return telemetry.active_incident


@app.post("/api/deploy")
async def deploy(request: DeployRequest):
    global is_patched
    is_patched = True
    await pool.reset()
    resolved = telemetry.resolve_incident()
    return {
        "status": "canary_deployed",
        "patch_id": request.patch_id,
        "canary_weight_percent": request.canary_weight_percent,
        "active_pool_stats": pool.stats(),
        "resolved_incident": resolved.incident_id if resolved else None,
        "message": "Patch applied successfully. Connection leak resolved."
    }


@app.post("/api/reset")
async def reset():
    global is_patched
    is_patched = False
    await pool.reset()
    telemetry.reset()
    return {"status": "reset", "is_patched": False, "pool": pool.stats()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("target_service.app:app", host="0.0.0.0", port=8001, reload=False)
