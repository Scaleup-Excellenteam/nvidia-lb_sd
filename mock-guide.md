# Mock Guide

# Windows (PowerShell)

**Prereqs:** Python 3.10+ and `uvicorn` installed in your venv.

1. **Service Discovery (port 7000)**

```powershell
cd service-discovery
py -m uvicorn app.main:app --reload --port 7000
```

2. **Dummy backends (to receive redirects)**

```powershell
# Terminal B
py -m http.server 9001
# Terminal C
py -m http.server 9002
```

3. **Load Balancer (port 8000)**

```powershell
cd load-balancer
$env:SERVICE_DISCOVERY_URL = "http://localhost:7000"
py -m uvicorn app.main:app --reload --port 8000
```

> If you’re using **CMD** instead of PowerShell:
> `set SERVICE_DISCOVERY_URL=http://localhost:7000`

4. **Test the flow**

```powershell
# Use curl.exe to avoid PowerShell’s Invoke-WebRequest alias
curl.exe -i "http://localhost:8000/r/demo-app/health?user=alice"
```

You should get `HTTP/1.1 307 Temporary Redirect` with `Location: http://127.0.0.1:9001/health?user=alice` (then 9002 on the next call, round-robin).

---

# Linux (also works on macOS)

**Prereqs:** Python 3.10+ and `uvicorn` installed in your venv.

1. **Service Discovery**

```bash
cd service-discovery
python3 -m uvicorn app.main:app --reload --port 7000
```

2. **Dummy backends**

```bash
# Terminal B
python3 -m http.server 9001
# Terminal C
python3 -m http.server 9002
```

3. **Load Balancer**

```bash
cd load-balancer
export SERVICE_DISCOVERY_URL="http://localhost:7000"
python3 -m uvicorn app.main:app --reload --port 8000
```

4. **Test**

```bash
curl -i "http://localhost:8000/r/demo-app/health?user=alice"
```

---

## Tips

* If a port is busy:

  * **Windows:** `netstat -ano | findstr :8000` → `taskkill /PID <pid> /F`
  * **Linux:** `lsof -i :8000` → `kill -9 <pid>`
* The route pattern is: `/r/{image_id}/{optional_path}` (query string is preserved).
* If SD returns no healthy backends, the LB responds `503`.

---

**Sources / further reading**
No external sources were used for these run steps.

**Further readings (broader context):**

* FastAPI: Redirects and Response types
* Uvicorn: ASGI server usage
* HTTPX: AsyncClient & connection pooling
* Prometheus Python client: exposing `/metrics`
* Service discovery patterns (client-side vs server-side) — overview videos/articles on YouTube and Wikipedia
