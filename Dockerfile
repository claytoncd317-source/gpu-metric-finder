# ── Base image ──
FROM python:3.12-slim

# ── Set working directory ──
WORKDIR /app

# ── Install system dependencies ──
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy requirements first for layer caching ──
COPY python/backend/requirements.txt .

# ── Install Python dependencies ──
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ──
COPY python/backend/ ./backend/
COPY static/ ./static/

# ── Set working directory to backend ──
WORKDIR /app/backend

# ── Expose port ──
EXPOSE 8000

# ── Health check ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Run the server ──
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]