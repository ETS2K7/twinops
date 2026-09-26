import asyncio
from fastapi.testclient import TestClient
from target_service.app import app

client = TestClient(app)


def test_target_service_lifecycle():
    # 1. Reset
    reset_resp = client.post("/api/reset")
    assert reset_resp.status_code == 200

    # 2. First 5 requests acquire connections but leak them (max pool = 5)
    for i in range(5):
        resp = client.post("/api/checkout", json={"cart_id": f"cart_{i}", "amount": 25.0})
        assert resp.status_code == 200, f"Request {i} failed unexpectedly"

    # 3. 6th request should fail due to connection pool exhaustion
    failed_resp = client.post("/api/checkout", json={"cart_id": "cart_overflow", "amount": 99.0})
    assert failed_resp.status_code == 500
    assert "ConnectionPoolExhaustedError" in failed_resp.text

    # 4. Check active incident
    incident_resp = client.get("/api/incident")
    assert incident_resp.status_code == 200
    incident = incident_resp.json()
    assert incident is not None
    assert incident["status"] == "OPEN"
    assert incident["service"] == "checkout-api"
    assert "ConnectionPoolExhaustedError" in incident["error_type"]
    print("Incident verified:", incident["incident_id"], incident["error_type"])

    # 5. Deploy patch
    deploy_resp = client.post("/api/deploy", json={"patch_id": "patch_pool_fix_001", "canary_weight_percent": 5})
    assert deploy_resp.status_code == 200
    assert deploy_resp.json()["status"] == "canary_deployed"

    # 6. Verify that under patched mode, repeated requests succeed without leaking
    for i in range(20):
        resp = client.post("/api/checkout", json={"cart_id": f"cart_patched_{i}", "amount": 50.0})
        assert resp.status_code == 200

    health_resp = client.get("/health")
    assert health_resp.json()["status"] == "healthy"
    assert health_resp.json()["is_patched"] is True
    print("Post-patch health verified: all 20 requests succeeded, pool healthy!")


if __name__ == "__main__":
    test_target_service_lifecycle()
    print("All Target Service integration tests passed!")
