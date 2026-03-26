import asyncio
import json
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
# Static files — MUST be mounted last
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="../../static", html=True), name="static")