# GPU Monitor — Real-Time NVIDIA GPU Performance Telemetry

> **AI-Assisted Learning Project** — Built from scratch using [Claude (Anthropic)](https://claude.ai) as a pair programming and teaching tool. Every component was worked through interactively to learn systems programming, cloud infrastructure, and GPU computing. The goal was understanding each layer deeply enough to explain it, not copy-pasting a finished product. See [Documentation & Resources](#documentation--resources) for all references used.

Live at **[gpumonitor.dev](http://gpumonitor.dev)** — real RTX 4090 telemetry streamed over WebSockets to a public dashboard via Cloudflare Tunnel. AWS SNS sends SMS alerts when thresholds are exceeded.

---

## How It Works

Three processes run simultaneously on a local machine with an RTX 4090:

```
C++ CUDA App  --TCP:8080-->  Python FastAPI  --cloudflared-->  gpumonitor.dev
(gpu_monitor)                (uvicorn :8000)                   (Cloudflare Edge)
```

1. **C++ binary** — runs a CUDA workload on the RTX 4090, streams JSON telemetry over a TCP socket on port 8080
2. **Python FastAPI** — reads GPU metrics via pynvml + C++ socket, serves the dashboard, streams to browsers via WebSocket
3. **cloudflared** — exposes localhost:8000 publicly at gpumonitor.dev with no port forwarding or static IP required

AWS ECS Fargate hosts a containerized fallback for CI/CD and mock-mode when the local machine is offline.

```
                    AWS Infrastructure (fallback)
               +------------------------------+
               |  ECR --> ECS Fargate         |
               |  ALB (port 80)               |
               |  CloudWatch Logs             |
               |  SNS SMS Alerts              |
               |  GitHub Actions CI/CD        |
               +------------------------------+
```

---

## Stack

| Layer | Technology |
|---|---|
| GPU Workload | C++17, CUDA 12.6, sm_89 (Ada Lovelace) |
| Socket Server | C++ TCP server (port 8080) |
| GPU Metrics | Python pynvml (NVML bindings) |
| Web Server | FastAPI + uvicorn + WebSockets |
| Frontend | Vanilla HTML/CSS/JS |
| Tunnel | Cloudflare Tunnel (cloudflared) |
| DNS | Cloudflare — gpumonitor.dev |
| Container | Docker (python:3.12-slim) |
| Registry | AWS ECR |
| Compute | AWS ECS Fargate (us-west-2) |
| Load Balancer | AWS ALB (port 80) |
| Alerts | AWS SNS SMS |
| IaC | Terraform 1.14.8, AWS provider ~> 5.0 |
| CI/CD | GitHub Actions |
| GPU | NVIDIA RTX 4090 (24GB, sm_89) |
| Dev Environment | WSL2 Ubuntu 24.04, CUDA Toolkit 12.6 |

---

## Project Structure

```
gpu_monitor/
├── .github/workflows/deploy.yml   # GitHub Actions CI/CD
├── cpp/
│   ├── include/cuda_workload.h    # CUDA extern C declaration
│   ├── src/
│   │   ├── main.cpp               # Entry point — socket thread + CUDA loop
│   │   ├── socket_server.cpp      # TCP server — streams JSON to Python
│   │   └── cuda_workload.cu       # CUDA kernel — stresses RTX 4090
│   └── CMakeLists.txt             # CMake — targets sm_89, C++17
├── python/backend/
│   ├── main.py                    # FastAPI — WebSocket, /health, /alert
│   ├── monitor.py                 # pynvml metrics + C++ socket client
│   └── requirements.txt
├── static/index.html              # Dashboard — terminal aesthetic
├── terraform/
│   ├── versions.tf                # Provider version pins
│   ├── variables.tf               # Input variables
│   ├── outputs.tf                 # ECR URL, ALB DNS, SNS ARN
│   ├── networking.tf              # VPC, subnets, IGW, security groups
│   ├── ecs.tf                     # ECR, ECS cluster, task, service, IAM
│   ├── alb.tf                     # ALB, target group, HTTP listener
│   └── sns.tf                     # SNS topic + SMS subscription
├── Dockerfile                     # python:3.12-slim, exposes 8000
├── start.sh                       # Starts all 3 processes at once
└── README.md
```

---

## WSL2 Setup — Full Build Commands

### Prerequisites

```bash
# CUDA Toolkit 12.6
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update && sudo apt install -y cuda-toolkit-12-6

# Build tools + CMake
sudo apt install -y cmake build-essential

# Python 3.12
sudo apt install -y python3.12 python3.12-venv

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Terraform
sudo apt install -y gnupg software-properties-common
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform

# Docker
sudo apt install -y docker.io
sudo usermod -aG docker $USER

# Cloudflare Tunnel
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

### Build C++ Project

```bash
cd ~/gpu_monitor/cpp
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### Python Environment

```bash
cd ~/gpu_monitor/python
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Cloudflare Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create gpu-monitor
cloudflared tunnel route dns gpu-monitor gpumonitor.dev
```

Config at `~/.cloudflared/config.yml`:

```yaml
tunnel: 9009b383-7f65-44fa-a389-ad67fbd49d88
credentials-file: /home/clayt/.cloudflared/9009b383-7f65-44fa-a389-ad67fbd49d88.json

ingress:
  - hostname: gpumonitor.dev
    service: http://localhost:8000
  - service: http_status:404
```

### AWS Configuration

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, us-west-2, json
```

### Terraform Infrastructure

```bash
cd ~/gpu_monitor/terraform
terraform init
terraform apply -var="alert_phone_number=+1YOURNUMBER"
```

---

## Running Locally

### One command

```bash
~/gpu_monitor/start.sh
```

### Manual (three terminals)

**Terminal 1 — C++ socket server**
```bash
~/gpu_monitor/cpp/build/gpu_monitor
```

**Terminal 2 — Python FastAPI**
```bash
cd ~/gpu_monitor/python/backend
source ~/gpu_monitor/python/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 3 — Cloudflare Tunnel**
```bash
cloudflared tunnel run gpu-monitor
```

Open **http://gpumonitor.dev** in any browser.

---

## Docker / ECS (Mock Mode)

When running in ECS Fargate (no GPU), the dashboard shows zeroed metrics with "No GPU Detected". NVML falls back gracefully without crashing.

```bash
# Build and push to ECR
cd ~/gpu_monitor
docker build -t gpu-monitor:latest .
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 563702590536.dkr.ecr.us-west-2.amazonaws.com
docker tag gpu-monitor:latest 563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor:latest
docker push 563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor:latest

# Tear down infrastructure
cd ~/gpu_monitor/terraform
terraform destroy -var="alert_phone_number=+1YOURNUMBER"
```

---

## AWS Infrastructure

All resources in `us-west-2`:

- VPC `10.0.0.0/16`, 2 public subnets (us-west-2a, us-west-2b), Internet Gateway
- ALB SG — port 80 open to internet; ECS SG — port 8000 from ALB SG only
- ALB — forwards port 80 to ECS port 8000 with a stable DNS hostname
- ECR — `gpu-monitor`, scan on push enabled
- ECS Fargate — 512 CPU / 1024MB, `desired_count = 1`
- IAM execution role (ECR + CloudWatch) and task role (SNS publish only)
- CloudWatch log group — 14 day retention
- SNS topic + SMS subscription

| Resource | Value |
|---|---|
| Account | 563702590536 |
| Region | us-west-2 |
| ECR | 563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor |
| ECS Cluster | gpu-monitor-cluster |
| ECS Service | gpu-monitor-service |
| ALB DNS | gpu-monitor-alb-394324184.us-west-2.elb.amazonaws.com |
| SNS ARN | arn:aws:sns:us-west-2:563702590536:gpu-monitor-alerts |
| VPC | vpc-0224a2ba2487d1cd5 |

---

## CI/CD

GitHub Actions triggers on every push to `main`:

1. Checkout code
2. Configure AWS credentials (from GitHub Secrets)
3. Login to ECR
4. Build + tag Docker image (`sha` + `latest`)
5. Push to ECR
6. Force ECS redeployment
7. Wait for `services-stable`

**Secrets required:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

---

## Alert Thresholds

| Metric | Warn | Alert | Notes |
|---|---|---|---|
| GPU Utilization | > 70% | > 90% | 16,384 CUDA cores |
| VRAM Usage | > 70% | > 90% | 24,564 MB GDDR6X |
| Temperature | > 75C | > 83C | Throttle at 83C, max 89C |
| Power Draw | > 70% limit | > 90% limit | Default TDP 450W |

Alert cooldown: 5 minutes per metric.

---

## Design Decisions

**Cloudflare Tunnel over ECS for live data** — ECS has no GPU. The tunnel exposes the local FastAPI server publicly with no inbound firewall rules required.

**ALB over direct ECS IP** — ECS task IPs change on every restart. ALB gives a stable DNS hostname.

**C++ socket server over shared memory** — sockets work locally and across machines, the same pattern used by GPU profilers like NSight.

**pynvml over nvidia-smi** — direct driver access, no CLI parsing, structured Python objects.

**NVML graceful fallback** — same codebase runs in ECS (mock mode) and locally (live GPU data).

**Split ALB + ECS security groups** — ECS only accepts traffic from the ALB SG, blocking direct access even if the task IP is discovered.

---

## Documentation & Resources

All code written from scratch with reference to official documentation only. No third-party snippets or tutorials copied.

### NVIDIA / CUDA
- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [NVML API Reference](https://docs.nvidia.com/deploy/nvml-api/)
- [pynvml Documentation](https://pypi.org/project/pynvml/)
- [NVIDIA Ada Lovelace Architecture Whitepaper](https://images.nvidia.com/akamai/products/geforce/ada/nvidia-ada-gpu-architecture-whitepaper.pdf)

### C++ / Sockets
- [POSIX Sockets (man7.org)](https://man7.org/linux/man-pages/man7/socket.7.html)
- [CMake Documentation](https://cmake.org/cmake/help/latest/)

### Python / FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Starlette WebSockets](https://www.starlette.io/websockets/)
- [uvicorn Documentation](https://www.uvicorn.org/)

### Docker
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Docker Python Best Practices](https://docs.docker.com/language/python/)

### AWS
- [ECS Fargate Developer Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ECR User Guide](https://docs.aws.amazon.com/AmazonECR/latest/userguide/)
- [ALB Documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [SNS Developer Guide](https://docs.aws.amazon.com/sns/latest/dg/)
- [IAM Reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [AWS CLI Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/index.html)

### Terraform
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Language Reference](https://developer.hashicorp.com/terraform/language)

### Cloudflare
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Cloudflare DNS Records](https://developers.cloudflare.com/dns/manage-dns-records/)
- [Cloudflare SSL/TLS Modes](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/)
- [Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/)

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [aws-actions/amazon-ecr-login](https://github.com/aws-actions/amazon-ecr-login)

---

## Developer

Clayton Christudass
- GitHub: [claytoncd317-source](https://github.com/claytoncd317-source)
- Location: Irvine, CA
