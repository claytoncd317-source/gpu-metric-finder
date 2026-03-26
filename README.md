# GPU Monitor

Real-time NVIDIA GPU performance monitor bridging a C++ CUDA workload with a Python dashboard.

## Vision
A professional GPU telemetry system where a C++ application (CUDA compute + game engine simulation) pushes graphical load onto the GPU while a Python monitor observes all four key metrics in real time — GPU utilization, VRAM usage, temperature, and power draw — served to a live web dashboard via WebSockets.

## WSL2 Setup Commands
```bash
# Verify WSL2 kernel
uname -r

# Install C++ build tools
sudo apt-get update
sudo apt-get install -y build-essential
sudo apt-get install -y cmake

# Add NVIDIA CUDA repo
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# Install CUDA Toolkit
sudo apt-get install -y cuda-toolkit-12-6

# Add CUDA to PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
nvcc --version
nvidia-smi
```

## Stack
- **C++** — TCP socket server + CUDA workload (sm_89 Ada Lovelace)
- **Python** — pynvml metrics + FastAPI WebSocket server
- **Frontend** — HTML/JS live dashboard
- **Target GPU** — NVIDIA RTX 4090 (24GB)