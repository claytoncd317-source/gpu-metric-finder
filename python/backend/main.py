import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from monitor import init_nvml, shutdown_nvml, get_gpu_metrics, cpp_client

# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_nvml()
    cpp_client.start()
    print("[GPU Monitor] NVML initialized, socket client started.")
    yield
    # Shutdown
    cpp_client.stop()
    shutdown_nvml()
    print("[GPU Monitor] Shutdown complete.")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="GPU Monitor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            metrics = get_gpu_metrics(0)
            cpp_data = cpp_client.get_latest()
            if cpp_data:
                metrics["cpp_telemetry"] = cpp_data
            await websocket.send_text(json.dumps(metrics))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("[GPU Monitor] Client disconnected.")

# ---------------------------------------------------------------------------
# Alert endpoint — sends SMS via AWS SNS
# ---------------------------------------------------------------------------

@app.post("/alert")
async def send_alert(payload: dict):
    import boto3
    topic_arn = os.environ.get("SNS_TOPIC_ARN")
    if not topic_arn:
        return {"status": "error", "message": "SNS_TOPIC_ARN not set"}
    sns = boto3.client("sns", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))
    sns.publish(TopicArn=topic_arn, Message=payload["message"])
    return {"status": "sent"}

# ---------------------------------------------------------------------------
# Static files — resolve path for both local and Docker environments
# ---------------------------------------------------------------------------

# Local dev:  running from python/backend/, static is ../../static
# Docker:     running from /app/backend/, static is /app/static
static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
if not os.path.isdir(static_dir):
    static_dir = "/app/static"

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")