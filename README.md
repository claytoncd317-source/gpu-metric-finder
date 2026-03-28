# GPU Monitor — Real-Time NVIDIA GPU Performance Telemetry

A full-stack GPU monitoring system bridging a C++ CUDA workload with a Python FastAPI backend, served live at [gpumonitor.dev](http://gpumonitor.dev) via Cloudflare Tunnel. Real RTX 4090 telemetry streams over WebSockets to a live web dashboard. AWS SNS sends SMS alerts when thresholds are exceeded.

---

## Project Vision

A professional GPU telemetry system where a C++ application (CUDA compute workload) pushes graphical load onto a local RTX 4090 while a Python monitor observes all four key metrics in real time — GPU utilization, VRAM usage, temperature, and power draw — served to a live web dashboard via WebSockets. The entire system is publicly accessible at a custom domain with no port forwarding or static IP required.

---

## Architecture

```
┌─────────────────────┐     TCP Socket (port 8080)     ┌──────────────────────┐
│   C++ App           │ ── JSON telemetry frames ────▶  │   Python Backend     │
│                     │                                  │                      │
│  • CUDA workload    │ ◀── control signals ────        │  • pynvml metrics    │
│  • Socket server    │                                  │  • FastAPI + WS      │
│  • RTX 4090 sm_89   │                                  │  • Static dashboard  │
└─────────────────────┘                                  └──────────────────────┘
                                                                  │
                                                        Cloudflare Tunnel (cloudflared)
                                                                  │
                                                         gpumonitor.dev
                                                        (Cloudflare DNS + Proxy)
                                                                  │
                                              ┌───────────────────────────────────┐
                                              │         AWS Infrastructure        │
                                              │  ECS Fargate (mock/web fallback)  │
                                              │  ALB → port 80                    │
                                              │  ECR Docker image                 │
                                              │  CloudWatch Logs                  │
                                              │  SNS SMS Alerts                   │
                                              │  GitHub Actions CI/CD             │
                                              └───────────────────────────────────┘
```

### How It Actually Works

The local machine runs three processes simultaneously:
1. **C++ binary** — launches a CUDA workload on the RTX 4090, starts a TCP socket server on port 8080 streaming JSON telemetry
2. **Python FastAPI** — reads GPU metrics via pynvml + C++ socket, serves the dashboard at port 8000, streams data to browsers via WebSocket
3. **cloudflared tunnel** — punches through NAT/firewall and exposes localhost:8000 publicly at `gpumonitor.dev` via Cloudflare's edge network

AWS ECS Fargate hosts a containerized version of the backend for CI/CD demonstration and mock-mode fallback when the local machine is offline.

---

## Stack

| Layer | Technology |
|---|---|
| GPU Workload | C++ 17, CUDA 12.6, sm_89 (Ada Lovelace) |
| Socket Server | C++ TCP socket server (port 8080) |
| GPU Metrics | Python pynvml (NVML bindings) |
| Web Server | Python FastAPI + uvicorn + WebSockets |
| Frontend | Vanilla HTML/CSS/JS (single file, terminal aesthetic) |
| Tunnel | Cloudflare Tunnel (cloudflared) |
| DNS | Cloudflare — `gpumonitor.dev` |
| Containerization | Docker (python:3.12-slim) |
| Registry | AWS ECR |
| Compute | AWS ECS Fargate (us-west-2) |
| Load Balancer | AWS ALB (port 80) |
| Alerts | AWS SNS → SMS |
| IaC | Terraform 1.14.8, AWS provider ~> 5.0 |
| CI/CD | GitHub Actions |
| GPU | NVIDIA GeForce RTX 4090 (24GB, sm_89) |
| Dev Environment | WSL2 Ubuntu 24.04, CUDA Toolkit 12.6 |

---

## Project Structure

```
gpu_monitor/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD pipeline
├── cpp/
│   ├── include/
│   │   └── cuda_workload.h     # Header — extern C function declaration
│   ├── src/
│   │   ├── main.cpp            # Entry point — starts socket thread + CUDA loop
│   │   ├── socket_server.cpp   # TCP socket server — streams JSON to Python
│   │   └── cuda_workload.cu    # CUDA kernel — stresses RTX 4090
│   └── CMakeLists.txt          # CMake build — targets sm_89, C++17
├── python/
│   └── backend/
│       ├── main.py             # FastAPI app — WebSocket, /health, /alert
│       ├── monitor.py          # pynvml metrics + C++ socket client
│       └── requirements.txt    # Python dependencies
├── static/
│   └── index.html              # Live dashboard — black/green/white terminal aesthetic
├── terraform/
│   ├── versions.tf             # Terraform + AWS provider version pins
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # ECR URL, ECS cluster, SNS ARN, VPC ID, ALB DNS
│   ├── networking.tf           # VPC, subnets, IGW, route tables, ALB + ECS security groups
│   ├── ecs.tf                  # ECR, ECS cluster, task definition, service, IAM
│   ├── alb.tf                  # ALB, target group, HTTP listener
│   └── sns.tf                  # SNS topic + SMS subscription
├── Dockerfile                  # python:3.12-slim, exposes 8000
├── .gitignore                  # Covers C++, Python, Terraform state, AWS creds
└── README.md                   # This file
```

---

## AWS Infrastructure (Terraform)

All infrastructure lives in `us-west-2`. Resources provisioned:

- **VPC** `10.0.0.0/16` with DNS hostnames enabled
- **2 Public Subnets** across `us-west-2a` and `us-west-2b`
- **Internet Gateway** + public route table
- **ALB Security Group** — port 80 open to internet
- **ECS Security Group** — port 8000 open from ALB SG only (not internet)
- **Application Load Balancer** — stable DNS name, forwards port 80 → ECS port 8000
- **ALB Target Group** — `target_type = "ip"` for Fargate, health checks `/health`
- **ALB HTTP Listener** — port 80 → target group
- **ECR Repository** — `gpu-monitor`, scan on push enabled
- **ECS Cluster** — `gpu-monitor-cluster`, Container Insights enabled
- **ECS Task Definition** — 512 CPU / 1024MB RAM, injects `SNS_TOPIC_ARN` env var
- **ECS Service** — `desired_count = 1`, wired to ALB target group
- **IAM Execution Role** — pulls ECR images, writes CloudWatch logs
- **IAM Task Role** — `sns:Publish` on the alerts topic only
- **CloudWatch Log Group** — `/ecs/gpu-monitor`, 14 day retention
- **SNS Topic** — `gpu-monitor-alerts`
- **SNS SMS Subscription** — phone number in E.164 format

### AWS Resource IDs
- **Account ID:** 563702590536
- **Region:** us-west-2
- **ECR URL:** `563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor`
- **ECS Cluster:** `gpu-monitor-cluster`
- **ECS Service:** `gpu-monitor-service`
- **ALB DNS:** `gpu-monitor-alb-394324184.us-west-2.elb.amazonaws.com`
- **SNS Topic ARN:** `arn:aws:sns:us-west-2:563702590536:gpu-monitor-alerts`
- **CloudWatch Log Group:** `/ecs/gpu-monitor`
- **VPC ID:** `vpc-0224a2ba2487d1cd5`

---

## Cloudflare Setup

### Domain
`gpumonitor.dev` registered via Cloudflare Registrar ($12.20/yr).

### Tunnel
Cloudflare Tunnel (`cloudflared`) exposes the local FastAPI server publicly without opening any firewall ports or needing a static IP.

- **Tunnel ID:** `9009b383-7f65-44fa-a389-ad67fbd49d88`
- **Tunnel name:** `gpu-monitor`
- **Credentials:** `~/.cloudflared/9009b383-7f65-44fa-a389-ad67fbd49d88.json`
- **Config:** `~/.cloudflared/config.yml`

```yaml
tunnel: 9009b383-7f65-44fa-a389-ad67fbd49d88
credentials-file: /home/clayt/.cloudflared/9009b383-7f65-44fa-a389-ad67fbd49d88.json

ingress:
  - hostname: gpumonitor.dev
    service: http://localhost:8000
  - service: http_status:404
```

### DNS
CNAME record for `gpumonitor.dev` points to the Cloudflare Tunnel (managed automatically by `cloudflared tunnel route dns`). Proxy status: orange cloud (proxied).

### SSL/TLS
Mode set to **Flexible** — Cloudflare handles HTTPS on its edge, communicates with the tunnel over HTTP. WebSockets enabled in Cloudflare Network settings.

---

## GitHub Repository

- **Repo:** `https://github.com/claytoncd317-source/gpu-metric-finder`
- **Branch:** `main`
- **GitHub Actions:** triggers on every push to `main`
- **Secrets required:**
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

### CI/CD Pipeline Steps
1. Checkout code
2. Configure AWS credentials from GitHub Secrets
3. Login to ECR
4. Build Docker image, tag with `${{ github.sha }}` and `latest`
5. Push both tags to ECR
6. Force ECS service redeployment
7. Wait for `services-stable` (health check passes)

---

## Running Locally (Live GPU Data)

Three processes must run simultaneously to serve real RTX 4090 data at `gpumonitor.dev`.

### Terminal 1 — C++ CUDA Socket Server
```bash
cd ~/gpu_monitor/cpp
mkdir -p build && cd build
cmake ..
make -j$(nproc)
./gpu_monitor
# Output: [GPU Monitor] Starting on port 8080... Launching CUDA workload...
```

### Terminal 2 — Python FastAPI Backend
```bash
cd ~/gpu_monitor/python/backend
source ../../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
# Output: Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3 — Cloudflare Tunnel
```bash
cloudflared tunnel run gpu-monitor
# Output: Registered tunnel connection ... location=lax
```

Then open `http://gpumonitor.dev` in any browser anywhere.

---

## Docker / ECS Deployment (Mock Mode)

When running in ECS Fargate (no GPU), the app serves the dashboard in mock mode — NVML falls back gracefully and the frontend shows zeroed metrics with "No GPU Detected" status.

### Build and Push Manually
```bash
cd ~/gpu_monitor
docker build -t gpu-monitor:latest .
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 563702590536.dkr.ecr.us-west-2.amazonaws.com
docker tag gpu-monitor:latest 563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor:latest
docker push 563702590536.dkr.ecr.us-west-2.amazonaws.com/gpu-monitor:latest
```

### Deploy Infrastructure
```bash
cd ~/gpu_monitor/terraform
terraform init
terraform plan -var="alert_phone_number=+1YOURNUMBER"
terraform apply -var="alert_phone_number=+1YOURNUMBER"
```

### Tear Down Infrastructure
```bash
cd ~/gpu_monitor/terraform
terraform destroy -var="alert_phone_number=+1YOURNUMBER"
```

---

## GPU Metrics & Alert Thresholds

| Metric | Warn | Alert | Notes |
|---|---|---|---|
| GPU Utilization | > 70% | > 90% | 16,384 CUDA cores on RTX 4090 |
| VRAM Usage | > 70% | > 90% | 24,564 MB total GDDR6X |
| Temperature | > 75°C | > 83°C | Throttle at 83°C, max junction 89°C |
| Power Draw | > 70% of limit | > 90% of limit | Default TDP 450W |

Alert cooldown: 5 minutes per metric to prevent SMS spam.

---

## Key Design Decisions

**Why Cloudflare Tunnel instead of ECS for live data?**
ECS Fargate has no GPU. The RTX 4090 is a local machine. Cloudflare Tunnel exposes the local FastAPI server to the internet without port forwarding, a static IP, or any inbound firewall rules — `cloudflared` makes an outbound connection to Cloudflare's edge and all traffic flows through that encrypted tunnel.

**Why keep ECS at all?**
CI/CD demonstration, mock-mode fallback when the local machine is offline, and a complete example of containerized cloud deployment for portfolio purposes.

**Why ALB over direct ECS public IP?**
ECS task IPs change on every restart. ALB provides a stable DNS name. This is the production-grade pattern — Cloudflare CNAME points to the ALB hostname which never changes.

**Why Cloudflare for DNS?**
Free SSL termination via proxy mode, DDoS protection, WebSocket proxying, and hides the origin IP. The tunnel means no inbound connections ever reach the local machine directly.

**Why C++ socket server instead of shared memory?**
Sockets work both locally and across machines. This is the same pattern used by GPU profilers like NSight — a lightweight telemetry server that any consumer (Python, another process, a remote machine) can connect to.

**Why pynvml over subprocess nvidia-smi?**
pynvml talks directly to the NVIDIA driver — no CLI parsing, no subprocess overhead, structured Python objects returned directly.

**Why NVML graceful fallback in monitor.py?**
ECS Fargate has no GPU. The fallback keeps the server alive and serving the dashboard without crashing when NVML is unavailable, enabling the same codebase to run in both environments.

**Why split ALB SG and ECS SG?**
Security group referencing — ECS only accepts traffic from the ALB SG, not from the open internet. This means even if someone discovers the ECS task's public IP, they can't bypass the ALB to hit the container directly.

---

## AI-Assisted Learning

This is an **AI-assisted learning project**. Every component was built as a hands-on exercise to learn systems programming, cloud infrastructure, and GPU computing from the ground up. [Claude (Anthropic)](https://claude.ai) was used throughout as a pair programming and teaching tool — explaining concepts, debugging errors, generating code scaffolding, and walking through design decisions in real time.

The goal was never to copy-paste a finished product, but to understand each layer deeply enough to explain it. All architectural decisions, debugging, and infrastructure operations were worked through interactively.

---

## Documentation & Resources

All code was written from scratch with reference to the following official documentation. No third-party code snippets or tutorials were copied.

### NVIDIA / CUDA
- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/) — CUDA kernel structure, thread/block/grid hierarchy, sm_89 architecture
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/) — memory access patterns, occupancy
- [NVML API Reference](https://docs.nvidia.com/deploy/nvml-api/) — GPU utilization, VRAM, temperature, power draw via C bindings
- [pynvml Documentation](https://pypi.org/project/pynvml/) — Python NVML bindings used in `monitor.py`
- [NVIDIA Ada Lovelace Architecture Whitepaper](https://images.nvidia.com/akamai/products/geforce/ada/nvidia-ada-gpu-architecture-whitepaper.pdf) — sm_89 compute capability, RTX 4090 specs

### C++ / Sockets
- [POSIX Sockets (man7.org)](https://man7.org/linux/man-pages/man7/socket.7.html) — `socket()`, `bind()`, `listen()`, `accept()`, `send()`
- [CMake Documentation](https://cmake.org/cmake/help/latest/) — `CMakeLists.txt` structure, `find_package(CUDA)`, target properties

### Python / FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/) — app structure, WebSocket endpoint, lifespan context manager, static files
- [Starlette WebSockets](https://www.starlette.io/websockets/) — underlying WebSocket implementation
- [uvicorn Documentation](https://www.uvicorn.org/) — ASGI server, `--host`, `--port`, `--reload` flags

### Docker
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/) — `FROM`, `COPY`, `RUN`, `CMD`, `EXPOSE`
- [Docker Python Best Practices](https://docs.docker.com/language/python/) — slim base images, venv in containers

### AWS
- [AWS ECS Fargate Developer Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) — task definitions, services, networking mode `awsvpc`
- [AWS ECR User Guide](https://docs.aws.amazon.com/AmazonECR/latest/userguide/) — image push/pull, lifecycle policies
- [AWS ALB Documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/) — listeners, target groups, `target_type = ip`
- [AWS SNS Developer Guide](https://docs.aws.amazon.com/sns/latest/dg/) — topic creation, SMS subscriptions, publish API
- [AWS IAM Reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/) — execution roles, task roles, least-privilege policies
- [AWS CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/) — log groups, retention policies, `awslogs` driver
- [AWS CLI Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/index.html) — `ecs`, `ec2`, `elbv2` commands used during debugging

### Terraform
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) — all `aws_*` resources used in this project
- [Terraform Language Reference](https://developer.hashicorp.com/terraform/language) — variables, outputs, data sources, `jsonencode()`

### Cloudflare
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — `cloudflared` setup, tunnel config, ingress rules
- [Cloudflare DNS Records](https://developers.cloudflare.com/dns/manage-dns-records/) — CNAME setup, proxy mode
- [Cloudflare SSL/TLS Modes](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/) — Flexible vs Full vs Off
- [Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/) — enabling WebSocket proxying on free plan

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions) — workflow syntax, secrets, `aws-actions/configure-aws-credentials`
- [aws-actions/amazon-ecr-login](https://github.com/aws-actions/amazon-ecr-login) — ECR authentication action

---

## Developer

Clayton Christudass
- GitHub: https://github.com/claytoncd317-source
- Location: Irvine, CA
