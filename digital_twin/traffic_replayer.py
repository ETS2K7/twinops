import asyncio
import time
from typing import Optional
import httpx


async def replay_traffic_async(
    client: httpx.AsyncClient,
    endpoint: str = "/api/checkout",
    request_count: int = 15,
    concurrency: int = 5
) -> dict:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    statuses: list[int] = []
    error_messages: list[str] = []

    async def send_single_request(index: int):
        async with semaphore:
            payload = {
                "cart_id": f"twin_cart_{index}_{int(time.time())}",
                "user_id": f"twin_usr_{index}",
                "amount": 49.99
            }
            start = time.time()
            try:
                resp = await client.post(endpoint, json=payload, timeout=3.0)
                duration = (time.time() - start) * 1000
                latencies.append(duration)
                statuses.append(resp.status_code)
                if resp.status_code >= 400:
                    error_messages.append(resp.text)
            except Exception as exc:
                duration = (time.time() - start) * 1000
                latencies.append(duration)
                statuses.append(500)
                error_messages.append(str(exc))

    tasks = [send_single_request(i) for i in range(request_count)]
    await asyncio.gather(*tasks)

    successful = sum(1 for s in statuses if 200 <= s < 400)
    failed = len(statuses) - successful
    error_rate = round((failed / len(statuses)) * 100, 1) if statuses else 0.0

    sorted_latencies = sorted(latencies) if latencies else [0.0]
    p99_idx = int(len(sorted_latencies) * 0.99)
    p99_latency = round(sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)], 1)

    return {
        "total_sent": len(statuses),
        "successful": successful,
        "failed": failed,
        "error_rate_percent": error_rate,
        "p99_latency_ms": p99_latency,
        "sample_errors": error_messages[:3]
    }
