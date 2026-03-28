#!/bin/bash
echo "[GPU Monitor] Starting C++ socket server..."
~/gpu_monitor/cpp/build/gpu_monitor &
CPP_PID=$!

sleep 2

echo "[GPU Monitor] Starting Python FastAPI..."
cd ~/gpu_monitor/python/backend
source ~/gpu_monitor/python/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
PYTHON_PID=$!

sleep 2

echo "[GPU Monitor] Starting Cloudflare Tunnel..."
cloudflared tunnel run gpu-monitor &
CF_PID=$!

echo "[GPU Monitor] All services running."
echo "  C++        PID: $CPP_PID"
echo "  Python     PID: $PYTHON_PID"
echo "  Cloudflare PID: $CF_PID"
echo ""
echo "Visit: http://gpumonitor.dev"
echo "Press Ctrl+C to stop all."

trap "kill $CPP_PID $PYTHON_PID $CF_PID 2>/dev/null; echo 'Stopped.'" SIGINT SIGTERM
wait
