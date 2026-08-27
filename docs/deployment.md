# FinDoc-RAG Deployment Guide

## Overview

This guide covers deploying FinDoc-RAG in production using Docker Compose with a single‑origin architecture (Nginx + FastAPI) behind a Cloudflare Named Tunnel.

## Prerequisites

- Docker Engine 24+ & Docker Compose v2+
- Linux host with NVIDIA GPU (for Ollama)
- Ollama installed on host with models:
  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3.2:3b
  ```
- Domain name managed on Cloudflare (for TLS + tunnel)

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd FinDoc-RAG

# 2. Configure environment
cp .env.example .env
# Edit .env with production values (see Environment Variables)

# 3. Build & start
docker compose up -d --build

# 4. Verify
curl http://localhost/health
curl http://localhost/ready
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_NAME` | Service name | `FinDoc-RAG` | No |
| `APP_ENV` | `development` / `production` | `development` | No |
| `DEBUG` | `true`/`false` | `False` | No |
| `LOG_LEVEL` | `DEBUG`,`INFO`,`WARNING`,`ERROR` | `INFO` | No |
| `OLLAMA_BASE_URL` | Host Ollama URL | `http://127.0.0.1:11434` | **Yes** |
| `LLM_MODEL` | Generation model | `llama3.2:3b` | No |
| `EMBEDDING_MODEL` | Embedding model | `nomic-embed-text` | No |
| `RERANKER_MODEL` | Cross‑encoder model | `cross-encoder/ms-marco-MiniLM-L-6-v2` | No |
| `DATABASE_URL` | PostgreSQL DSN | `postgresql://postgres:postgres@localhost:5432/findoc_rag` | **Yes** |
| `VECTOR_STORE_PATH` | FAISS/Chunks path | `./data/vector_store` | No |
| `RAW_DATA_PATH` | Raw PDF storage | `./data/raw` | No |
| `MAX_UPLOAD_SIZE_MB` | Max PDF size | `50` | No |
| `CORS_ORIGINS` | Comma‑separated origins | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173` | **Yes (prod)** |
| `RATE_LIMITING_ENABLED` | `true`/`false` | `True` | No |
| `RATE_LIMIT_CHAT` | e.g. `30/minute` | `30/minute` | No |
| `RATE_LIMIT_UPLOAD` | e.g. `10/minute` | `10/minute` | No |
| `RATE_LIMIT_DELETE` | e.g. `10/minute` | `10/minute` | No |

**Production `.env` example**
```dotenv
APP_NAME=FinDoc-RAG
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO
OLLAMA_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=llama3.2:3b
EMBEDDING_MODEL=nomic-embed-text
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
DATABASE_URL=postgresql://postgres:strong_password@127.0.0.1:5432/findoc_rag
VECTOR_STORE_PATH=/app/data/vector_store
RAW_DATA_PATH=/app/data/raw
MAX_UPLOAD_SIZE_MB=50
CORS_ORIGINS=https://yourdomain.com
RATE_LIMITING_ENABLED=True
RATE_LIMIT_CHAT=30/minute
RATE_LIMIT_UPLOAD=10/minute
RATE_LIMIT_DELETE=10/minute
```

## Docker Compose Services

| Service | Image | Ports | Volumes | Network |
|---------|-------|-------|---------|---------|
| `postgres` | `postgres:16-alpine` | `5432:5432` | `postgres_data` | bridge |
| `app` | built from `Dockerfile` | `8000` (host) | `./data/raw`, `./data/vector_store` | **host** |
| `frontend` | built from `frontend/Dockerfile` (nginx) | `80` (host) | — | **host** |

`network_mode: host` on `app` and `frontend` lets them reach host‑local Ollama (`127.0.0.1:11434`) and PostgreSQL (`127.0.0.1:5432`).

## Cloudflare Named Tunnel (Production TLS)

### 1. Install & Authenticate
```bash
sudo pacman -S cloudflared   # Arch/EndeavourOS
# or: brew install cloudflared / apt install cloudflared
cloudflared tunnel login
```

### 2. Create Tunnel
```bash
cloudflared tunnel create findoc-rag
# Note the Tunnel UUID printed
```

### 3. Route DNS
```bash
cloudflared tunnel route dns findoc-rag yourdomain.com
# optional: www.yourdomain.com
```

### 4. Configure Tunnel (`~/.cloudflared/config.yml`)
```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/<user>/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: yourdomain.com
    service: http://127.0.0.1:80
    originRequest:
      connectTimeout: 30s
      http2Origin: false
  - service: http_status:404
```

### 5. Run as Systemd Service
```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

All traffic now reaches `https://yourdomain.com` → Cloudflare → `http://127.0.0.1:80` (Nginx) → FastAPI (`/api/*`).

## Health & Readiness Checks

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `GET /health` | Liveness | `200 { "status":"healthy" }` |
| `GET /ready` | Readiness (FAISS, BM25, DB, Ollama) | `200 { "status":"ready", "checks":{...} }` or `503` |

## Volume Persistence

| Volume | Host Path | Container Path | Purpose |
|--------|-----------|----------------|---------|
| `postgres_data` | Docker volume | `/var/lib/postgresql/data` | PostgreSQL data |
| `./data/raw` | `./data/raw` | `/app/data/raw` | Uploaded PDFs |
| `./data/vector_store` | `./data/vector_store` | `/app/data/vector_store` | FAISS + chunks.jsonl |

## Backup & Restore

### PostgreSQL
```bash
# Backup
docker exec findoc-rag-db pg_dump -U postgres findoc_rag > backup_$(date +%F).sql

# Restore
docker exec -i findoc-rag-db psql -U postgres findoc_rag < backup_2025-08-27.sql
```

### Vector Store & Raw PDFs
```bash
tar -czf vector_store_$(date +%F).tar.gz data/vector_store
tar -czf raw_pdfs_$(date +%F).tar.gz data/raw
```

## Scaling Notes

- **Horizontal API**: Run multiple `app` replicas behind a load balancer; replace in‑memory rate limiter with Redis.
- **Ollama**: Run on dedicated GPU node; expose via internal network.
- **PostgreSQL**: Enable read replicas; use PgBouncer for connection pooling.
- **Rate Limiter**: Swap in‑memory `InMemoryRateLimiter` for Redis‑backed sliding window.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `/ready` returns 503 | `docker logs findoc-rag-app` – verify FAISS files, PostgreSQL connectivity, Ollama reachable |
| Upload fails | `docker logs findoc-rag-app` – PDF magic bytes, size limit, disk space |
| Frontend blank | `docker logs findoc-rag-frontend` – Nginx config, `proxy_pass` to `http://127.0.0.1:8000` |
| Ollama unreachable | `curl http://127.0.0.1:11434/api/tags` on host; ensure Ollama service running |

## Security Checklist (Pre‑Deploy)

- [ ] Strong `POSTGRES_PASSWORD` in `.env`
- [ ] `CORS_ORIGINS` limited to production domain(s)
- [ ] `RATE_LIMITING_ENABLED=True`
- [ ] Cloudflare “Always Use HTTPS” enabled
- [ ] Cloudflare WAF / Bot Fight Mode enabled
- [ ] Host firewall: only ports 80/443 (Cloudflare) + 22 (SSH) open
- [ ] Regular `docker compose pull && docker compose up -d --build` for base image updates

---

*Last updated: 2025‑08‑27*