# Production Cloudflare Named Tunnel Guide for FinDoc-RAG

This guide details the setup for exposing FinDoc-RAG securely to the public internet using a **Named Cloudflare Tunnel** with custom domains, automatic SSL/TLS encryption, and zero open router ports.

---

## 1. Architecture

```
Internet Users (HTTPS)
         │
         ▼
Cloudflare Edge (DDoS protection, SSL/TLS termination)
         │
         ▼ (Encrypted Tunnel over QUIC/HTTP2)
cloudflared daemon (running on host)
         │
         ▼
   http://127.0.0.1:80  (Nginx reverse proxy)
         │
         ├── Serves React production build (SPA)
         └── Proxies /api/* → http://127.0.0.1:8000 (FastAPI Backend)
```

---

## 2. Prerequisites

- Installed `cloudflared` CLI (`sudo pacman -S cloudflared` on Arch / EndeavourOS).
- A domain name managed on Cloudflare.
- Active FinDoc-RAG Docker Compose stack (frontend + backend + postgres).

---

## 3. Step-by-Step Deployment

### Step 1: Authenticate with Cloudflare
```bash
cloudflared tunnel login
```
This opens your browser to select your Cloudflare domain and creates a certificate file at `~/.cloudflared/cert.pem`.

### Step 2: Create the Named Tunnel
```bash
cloudflared tunnel create findoc-rag
```
Output gives your `<TUNNEL_UUID>` and creates a credentials JSON at `~/.cloudflared/<TUNNEL_UUID>.json`.

### Step 3: Configure DNS Route
```bash
# Route the apex (or www) domain to the tunnel
cloudflared tunnel route dns findoc-rag yourdomain.com
# Optionally also www
cloudflared tunnel route dns findoc-rag www.yourdomain.com
```

### Step 4: Configure the Tunnel
Copy `deploy/cloudflare/config.example.yml` to `~/.cloudflared/config.yml` and populate your `<TUNNEL_UUID>` and `<YOUR_DOMAIN>`:

```yaml
tunnel: 12345678-abcd-1234-abcd-1234567890ab
credentials-file: /home/saptak/.cloudflared/12345678-abcd-1234-abcd-1234567890ab.json

ingress:
  - hostname: yourdomain.com
    service: http://127.0.0.1:80
    originRequest:
      connectTimeout: 30s
      http2Origin: false
  - service: http_status:404
```

### Step 5: Test and Run the Tunnel
```bash
# Run foreground test
cloudflared tunnel run findoc-rag

# Or install as a systemd service for 24/7 reliability
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### Step 6: Environment Variables for Production
1. Backend `.env` (or docker-compose env) – allow the production frontend origin for CORS (same‑origin requests normally don’t need CORS, but keep for safety):
   ```env
   CORS_ORIGINS=https://yourdomain.com,http://localhost:5173
   ```
2. Frontend production build uses relative API paths, so no `VITE_API_BASE_URL` is required (it is empty in `.env.production`).

3. Build and start the full stack:
   ```bash
   docker compose up -d --build
   ```

---

## 4. Local Development Workflow (unchanged)

- Backend: `docker compose up -d postgres app` (or run `uvicorn app.main:app --reload` locally).
- Frontend: `cd frontend && npm run dev` (Vite on `http://localhost:5173`).
- Frontend `.env` keeps `VITE_API_BASE_URL=http://localhost:8000`.
- CORS origins in backend include `http://localhost:5173`.

No Cloudflare tunnel needed for local development.

---

## 5. Production Deployment Workflow

1. Ensure `.env` files for backend and frontend are set for production (see Step 6).
2. Build and start stack:
   ```bash
   docker compose up -d --build
   ```
3. Verify:
   - `curl http://localhost/health` → healthy
   - `curl http://localhost/ready` → ready
   - `curl -X POST http://localhost/api/v1/chat -H "Content-Type: application/json" -d '{"query":"test"}'`
4. Start Cloudflare tunnel (systemd service) – traffic reaches `http://127.0.0.1:80`.

All external access goes through the single domain `https://yourdomain.com`.