# Docker Mock Guide
# 0) Create `.dockerignore` (repo root)

**What it does:** keeps Python caches, venvs, logs, etc. out of your images so builds are fast and clean.

**Template contents:**

```
__pycache__/
*.pyc
*.pyo
*.pyd
*.log
*.sqlite*
dist/
build/
.env
.venv/
venv/
.idea/
.vscode/
.mypy_cache/
.pytest_cache/
```

**Windows (PowerShell):**

```powershell
@'
__pycache__/
*.pyc
*.pyo
*.pyd
*.log
*.sqlite*
dist/
build/
.env
.venv/
venv/
.idea/
.vscode/
.mypy_cache/
.pytest_cache/
'@ | Set-Content -Encoding UTF8 .dockerignore
```

**Linux/macOS (bash/zsh):**

```bash
cat > .dockerignore <<'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
*.log
*.sqlite*
dist/
build/
.env
.venv/
venv/
.idea/
.vscode/
.mypy_cache/
.pytest_cache/
EOF
```

---

# 1) Prerequisites

* **Windows:** Install Docker Desktop (WSL2 backend recommended).
* **Linux/macOS:** Docker Engine + Compose plugin. Check:

  ```bash
  docker --version && docker compose version
  ```

Make sure your repo has:

* `service-discovery/Dockerfile`
* `load-balancer/Dockerfile`
* A valid `docker-compose.yml` (with `dockerfile:` nested under each service’s `build:`).

---

# 2) Build & start the stack

**Windows (PowerShell) or Linux/macOS (bash):**

```bash
# from the repository root (where docker-compose.yml lives)
docker compose up --build -d
```

Check status:

```bash
docker compose ps
docker compose logs -f load-balancer
```

> Tip: In your compose, the LB should have `SERVICE_DISCOVERY_URL=http://service-discovery:7000`.

---

# 3) (Optional) Seed the demo backends in Service-Discovery

Only do this if your SD doesn’t auto-seed.

**Windows (PowerShell):**

```powershell
curl.exe -s -X POST http://localhost:7000/registry/endpoints `
  -H "Content-Type: application/json" `
  -d "{\"id\":\"demo-9001\",\"image_id\":\"demo-app\",\"host\":\"localhost\",\"port\":9001,\"status\":\"HEALTHY\"}"

curl.exe -s -X POST http://localhost:7000/registry/endpoints `
  -H "Content-Type: application/json" `
  -d "{\"id\":\"demo-9002\",\"image_id\":\"demo-app\",\"host\":\"localhost\",\"port\":9002,\"status\":\"HEALTHY\"}"
```

**Linux/macOS:**

```bash
curl -s -X POST http://localhost:7000/registry/endpoints \
  -H 'Content-Type: application/json' \
  -d '{"id":"demo-9001","image_id":"demo-app","host":"localhost","port":9001,"status":"HEALTHY"}'

curl -s -X POST http://localhost:7000/registry/endpoints \
  -H 'Content-Type: application/json' \
  -d '{"id":"demo-9002","image_id":"demo-app","host":"localhost","port":9002,"status":"HEALTHY"}'
```

---

# 4) Test the flow

**Windows (PowerShell):**

```powershell
curl.exe -i "http://localhost:8000/r/demo-app/health?user=alice"
```

**Linux/macOS:**

```bash
curl -i "http://localhost:8000/r/demo-app/health?user=alice"
```

**Expected:** `HTTP/1.1 307 Temporary Redirect` and a `Location: http://localhost:9001/...` (next request should round-robin to `9002`).

You can also test in a browser:
`http://localhost:8000/r/demo-app/` → you should land on one of the backends.

---

# 5) Stop & clean

```bash
docker compose down     # stop
docker compose down -v  # stop + remove named/anon volumes if you created any
```

---

## Troubleshooting (quick)

* **Port already in use:**

  * Windows: `netstat -ano | findstr :8000` → `taskkill /PID <pid> /F`
  * Linux/macOS: `lsof -i :8000` → `kill -9 <pid>`
* **Compose can’t find Dockerfile:** ensure:

  ```yaml
  build:
    context: .
    dockerfile: service-discovery/Dockerfile
  ```
* **“Additional property dockerfile is not allowed”** → `dockerfile:` must be **inside** `build:`, not next to it.
* **Healthchecks failing:** `docker compose logs -f service-discovery` and `... load-balancer` to see startup errors.

---

## References & further reading

* Docker docs: “.dockerignore” file; “Compose file build reference”; “Docker Compose CLI”; “Healthcheck”
* FastAPI docs: `RedirectResponse` and deployment with Uvicorn
* MDN: HTTP 307 Temporary Redirect (vs 302)
* Wikipedia: “Service discovery”
* YouTube: “FastAPI + Docker Compose (full tutorial)”, “Docker Compose in 100 seconds” (good visual refresh)
