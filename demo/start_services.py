import asyncio
import uvicorn
from target_service.app import app as target_app
from mcp_server.server import app as mcp_app


async def run_services():
    config_mcp = uvicorn.Config(mcp_app, host="0.0.0.0", port=8000, log_level="warning")
    server_mcp = uvicorn.Server(config_mcp)

    config_target = uvicorn.Config(target_app, host="0.0.0.0", port=8001, log_level="warning")
    server_target = uvicorn.Server(config_target)

    print("=" * 70)
    print("🚀 TWINOPS LIVE SERVICES LAUNCHED")
    print("=" * 70)
    print("  • Target Checkout Service:  http://localhost:8001")
    print("    ↳ Health:                 http://localhost:8001/health")
    print("    ↳ Metrics:                http://localhost:8001/metrics")
    print("    ↳ Incident API:           http://localhost:8001/api/incident")
    print("  • TwinOps FastMCP Server:   http://localhost:8000/sse")
    print("    ↳ Tool Endpoint:          http://localhost:8000/sse")
    print("  • TrueForge UI:             http://localhost:8790")
    print("=" * 70)
    print("\nServices running. Press Ctrl+C to stop.")

    await asyncio.gather(
        server_mcp.serve(),
        server_target.serve()
    )


if __name__ == "__main__":
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
