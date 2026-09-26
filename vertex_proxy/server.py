"""OpenAI-compatible Vertex AI proxy for TrueForge."""

import json
import os
import time
from typing import Any
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

ADC_PATH = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
PROJECT_ID = os.getenv("VERTEXAI_PROJECT", "project-e2e83680-ef71-4646-8b3")
LOCATION = os.getenv("VERTEXAI_LOCATION", "us-central1")

app = FastAPI(title="Vertex AI OpenAI Proxy")

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0}


def get_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not os.path.exists(ADC_PATH):
        raise RuntimeError(f"ADC credentials not found at {ADC_PATH}")

    with open(ADC_PATH) as f:
        creds = json.load(f)

    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in - 300
    return token


@app.get("/health")
def health():
    return {"status": "ok", "provider": "vertex-ai", "project": PROJECT_ID}


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "google/gemini-2.5-flash",
                "object": "model",
                "created": 1700000000,
                "owned_by": "google",
            },
            {
                "id": "gemini-2.5-flash",
                "object": "model",
                "created": 1700000000,
                "owned_by": "google",
            },
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    token = get_access_token()

    model = body.get("model", "google/gemini-2.5-flash")
    if not model.startswith("google/"):
        body["model"] = f"google/{model}"

    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1"
        f"/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/openapi/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    is_stream = body.get("stream", False)

    client = httpx.AsyncClient(timeout=120.0)

    if is_stream:
        req = client.build_request("POST", url, headers=headers, json=body)
        resp = await client.send(req, stream=True)

        async def stream_generator():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=resp.status_code,
            headers={
                k: v
                for k, v in resp.headers.items()
                if k.lower() in ["content-type", "cache-control"]
            },
        )
    else:
        try:
            resp = await client.post(url, headers=headers, json=body)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={"Content-Type": "application/json"},
            )
        finally:
            await client.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
