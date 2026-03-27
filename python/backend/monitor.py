import socket
import json
import time
import threading

# ---------------------------------------------------------------------------
# NVML setup — graceful fallback if no GPU present (e.g. ECS Fargate)
# ---------------------------------------------------------------------------

NVML_AVAILABLE = False

try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
    pynvml.nvmlShutdown()
except Exception:
    print("[GPU Monitor] WARNING: NVML not available — running in mock mode (no GPU detected)")


def init_nvml():
    if NVML_AVAILABLE:
        pynvml.nvmlInit()


def shutdown_nvml():
    if NVML_AVAILABLE:
        pynvml.nvmlShutdown()


def get_gpu_metrics(index=0):
    """
    Returns live GPU metrics if NVML is available.
    Returns zeroed mock metrics if running without a GPU (e.g. ECS Fargate on CPU).
    """
    if not NVML_AVAILABLE:
        return {
            "name":          "No GPU Detected (Mock Mode)",
            "gpu_util":      0,
            "vram_used_mb":  0.0,
            "vram_total_mb": 1.0,   # non-zero to avoid division by zero in dashboard
            "temperature":   0,
            "power_w":       0.0,
            "power_limit_w": 1.0,   # non-zero to avoid division by zero in dashboard
            "timestamp":     time.time(),
        }

    handle = pynvml.nvmlDeviceGetHandleByIndex(index)

    name = pynvml.nvmlDeviceGetName(handle)
    if isinstance(name, bytes):
        name = name.decode("utf-8")

    util      = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem       = pynvml.nvmlDeviceGetMemoryInfo(handle)
    temp      = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
    power_mw       = pynvml.nvmlDeviceGetPowerUsage(handle)
    power_limit_mw = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle)

    return {
        "name":          name,
        "gpu_util":      util.gpu,
        "vram_used_mb":  round(mem.used  / 1024 ** 2, 1),
        "vram_total_mb": round(mem.total / 1024 ** 2, 1),
        "temperature":   temp,
        "power_w":       round(power_mw       / 1000.0, 1),
        "power_limit_w": round(power_limit_mw / 1000.0, 1),
        "timestamp":     time.time(),
    }


# ---------------------------------------------------------------------------
# C++ socket client
# ---------------------------------------------------------------------------

class CppSocketClient:
    """
    Connects to the C++ socket server and reads JSON telemetry frames.
    Runs on its own thread so it never blocks the FastAPI event loop.
    """

    def __init__(self, host="127.0.0.1", port=8080):
        self.host    = host
        self.port    = port
        self.running = False
        self.latest  = {}
        self._thread = None
        self._lock   = threading.Lock()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def get_latest(self):
        with self._lock:
            return dict(self.latest)

    def _read_loop(self):
        while self.running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.host, self.port))
                    buffer = ""
                    while self.running:
                        chunk = s.recv(4096).decode("utf-8")
                        if not chunk:
                            break
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            if line.strip():
                                data = json.loads(line)
                                with self._lock:
                                    self.latest = data
            except (ConnectionRefusedError, OSError):
                # C++ server not up yet — retry every 2 seconds
                time.sleep(2)


# ---------------------------------------------------------------------------
# Shared instances
# ---------------------------------------------------------------------------

cpp_client = CppSocketClient()