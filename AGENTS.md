# AGENTS.md — Team 2 (Load Balancer + Service Discovery)

> Purpose: Define **automation agents** (LLM- or bot-driven) that operate our platform safely: what each agent does, what APIs it may call, what inputs/outputs look like, and guardrails. This doc is implementation-agnostic (works with Slack bots, GitHub Actions, Make targets, or any agents framework).

---

## 0) Scope & Principles

* **Stateless-by-default**: agents keep no durable state; use Redis/HTTP APIs.
* **API-first**: agents ONLY use documented endpoints in this repo and Redis keys noted here.
* **Safety**: admin actions require `X-Platform-Token`. Never expose tokens or raw Redis values in user channels.
* **Observability**: agents emit JSON logs (include `trace_id`, `agent`, `action`, `target`).
* **Idempotent**: retries allowed for GET/PUT; avoid retrying non-idempotent actions unless explicitly marked safe.
* **HITL** (human-in-the-loop) for destructive ops: policy deletes, chaos ops, or rate changes >50%.

---

## 1) Endpoints & Keys (allowed agent surface)

### HTTP — Service Discovery (SD)

* `POST  SD  /v1/services/register`
* `PUT   SD  /v1/services/{instance_id}/heartbeat`
* `DELETE SD  /v1/services/{instance_id}`
* `GET   SD  /v1/services{?name,image,status}`
* `GET   SD  /v1/services/{name}/instances`
* `GET   SD  /v1/topology`
* `GET   SD  /readyz`, `/metrics`

### HTTP — Load Balancer (LB)

* `PUT  LB /v1/policy/{image}` — admin only
* `GET  LB /v1/policy/{image}`
* `POST LB /v1/route/preview`
* `GET  LB /v1/stats/images?window=1m|5m|1h`
* `GET  LB /v1/stats/instances?image=...&window=...`
* `POST LB /v1/billing/export?window=1h`
* `ANY  LB /g/{image}/{path...}` (edge proxy)
* `GET  LB /readyz`, `/metrics`

### Redis (read/write)

* **Policies**: `policy:{image}` → JSON `{image, algorithm, weights?, sticky_key?}`
* **LB Counters**: `lb:cnt:{window}:{metric}:{key}` (agents read)
* **SD Registry** (read-only for agents): `svc:{name}:instances` (SET), `inst:{id}` (JSON), `inst_expiry` (ZSET)

---

## 2) Agent Directory

| Agent                      | Role                                                            | Critical APIs                 | Auth                          | HITL?                     |
| -------------------------- | --------------------------------------------------------------- | ----------------------------- | ----------------------------- | ------------------------- |
| **sd-agent**               | Register/heartbeat platform instances on behalf of Orchestrator | SD register/heartbeat/delete  | none                          | no                        |
| **lb-policy-agent**        | Create/update per-image routing policy                          | `PUT /v1/policy/{image}`      | `X-Platform-Token`            | for deletes/major changes |
| **lb-stats-agent**         | Summarize RPS/bytes/errors for dashboards                       | `GET /v1/stats/*`, `/metrics` | none                          | no                        |
| **billing-export-agent**   | Produce hourly usage exports to Team 4                          | `POST /v1/billing/export`     | `X-Platform-Token` (if gated) | no                        |
| **health-agent**           | Watch `/readyz` and raise alerts                                | `/readyz` (SD & LB)           | none                          | no                        |
| **trafficgen-agent** (dev) | Generate synthetic load for smoke tests                         | `/g/{image}/...`              | none                          | yes (prod)                |
| **chaos-agent** (opt)      | TTL/stop instances to verify failover                           | SD APIs                       | token if extended             | yes                       |
| **release-agent**          | CI/CD build, test, compose lifecycle                            | Make/Compose                  | CI secret                     | yes for prod              |
| **incident-bot**           | One-click runbooks in incidents                                 | Mix of above                  | token                         | yes                       |

---

## 3) Global Config (env)

```
AGENT_SD_BASE      = http://service-discovery:8001
AGENT_LB_BASE      = http://load-balancer:8000
AGENT_REDIS_URL    = redis://redis:6379/0
AGENT_PLATFORM_TOKEN= (matches .env PLATFORM_TOKEN)
AGENT_REQUEST_TIMEOUT_S= 5
AGENT_RETRY        = 2
AGENT_USER_CHANNEL = #team2-ops (or Slack webhook URL)
```

---

## 4) Message Contract (agent <-> human)

### Common fields (all agents)

```json
{
  "agent": "lb-policy-agent",
  "action": "set-policy",
  "trace_id": "${uuid}",
  "when": "2025-08-17T10:15:30Z",
  "request": { /* action-specific */ },
  "result": { /* outputs */ },
  "status": "ok|error",
  "error": {"code": "...", "detail": "..."}
}
```

### Error codes (subset)

* `not_ready` (dependency not ready)
* `unauthorized` (token mismatch)
* `not_found` (service/image)
* `policy_invalid` (schema/weights)
* `backend_unreachable`

---

## 5) Agent Specs

### 5.1 sd-agent (Orchestrator helper)

**Goal**: Keep SD registry accurate via register/heartbeat/delete.

**Inputs**

```json
{
  "instances": [
    {
      "name": "video-svc",
      "image": "img.video.svc",
      "instance_id": "i1",
      "host": "backend1",
      "port": 8080,
      "region": "eu-central",
      "metadata": {"weight": 2},
      "ttl_seconds": 30
    }
  ]
}
```

**Outputs**

```json
{"registered": 1, "expires_at": "2025-08-17T10:20:30Z"}
```

**Algorithm (pseudo)**

1. `GET SD /readyz` → require `ok`.
2. For each instance: `POST /v1/services/register`.
3. Start periodic heartbeat (every `ttl_seconds/2`).
4. On failures: retry `AGENT_RETRY` times; escalate to `AGENT_USER_CHANNEL` if still failing.

**Guards**: Deny duplicate `instance_id` unless `name,image` match.

---

### 5.2 lb-policy-agent

**Goal**: Manage routing policy per image.

**Inputs**

```json
{
  "image": "img.video.svc",
  "algorithm": "weighted_rr",
  "weights": {"i1": 2, "i2": 1},
  "sticky_key": null
}
```

**Outputs**

```json
{"ok": true, "policy": {"image":"img.video.svc","algorithm":"weighted_rr","weights":{"i1":2,"i2":1}}
}
```

**Steps**

1. Validate: `algorithm ∈ {round_robin, least_conn, weighted_rr}`; weights are integers ≥1; at least one live instance for image (optional check via SD).
2. `PUT LB /v1/policy/{image}` with header `X-Platform-Token: ${AGENT_PLATFORM_TOKEN}`.
3. Confirm with `GET LB /v1/policy/{image}`.
4. Announce success in ops channel with diff.

**HITL**: If changing algorithm between fundamentally different classes (e.g., least\_conn→weighted\_rr) or if any weight delta >50%, require manual `approve: yes` flag.

---

### 5.3 lb-stats-agent

**Goal**: Provide snapshots for dashboards.

**Inputs**

```json
{"window": "1m"}
```

**Outputs**

```json
[
  {"image":"img.video.svc","rps_avg":8,"bytes_tx":12000,"req_count":480,"errors_4xx":2,"errors_5xx":0}
]
```

**Steps**

1. `GET LB /v1/stats/images?window={window}`
2. Format table (CSV/Markdown) and post to channel.
3. (Optional) For a specific image, call `/v1/stats/instances` and include top N instances.

---

### 5.4 billing-export-agent

**Goal**: Produce an hourly export and handoff to Team 4 Billing.

**Schedule**: hourly at :05.

**Steps**

1. `POST LB /v1/billing/export?window=1h`.
2. Validate against `contracts/lb_billing_export.schema.json`.
3. Ship to Billing endpoint (S3/HTTP) — endpoint configured externally.
4. Emit checksum and store pointer in artifact store.

**Failure policy**: If export fails, retry 3x with exponential backoff, then alert.

---

### 5.5 health-agent

**Goal**: Alert when SD or LB not ready.

**Steps**

1. Every 30s: `GET /readyz` for SD and LB.
2. If response != `ok`, create incident thread with context (recent deploy? Redis health?).
3. Close alert after 3 consecutive successes.

---

### 5.6 trafficgen-agent (dev only)

**Goal**: Generate synthetic requests to validate routing.

**Inputs**

```json
{"image":"img.video.svc","path":"/api/health","rps":50,"duration_s":60}
```

**Steps**

1. Spawn N workers (async) sending `GET /g/{image}/{path}`.
2. During run, poll `/v1/stats/images` every 10s.
3. Report final distribution and p95 if observed via client timings.

**Guard**: Deny in production unless `allow_prod=true` with HITL approval.

---

### 5.7 chaos-agent (optional)

**Goal**: Validate failover by letting instances expire or removing them.

**Actions**

* `expire-instance {instance_id}` → stop heartbeats and wait >TTL.
* `delete-instance {instance_id}` → `DELETE /v1/services/{instance_id}` (HITL required).

**Success**: LB continues to serve 200s from remaining healthy instances; stats reflect failover.

---

### 5.8 release-agent (CI)

**Goal**: Build/test/deploy via Compose.

**Pipeline**

1. `uv run pytest` (both services)
2. `docker compose build --pull`
3. `docker compose up -d` in staging
4. Health checks → smoke tests with trafficgen-agent
5. Manual gate → prod compose rollout

---

### 5.9 incident-bot

**Goal**: One-click runbooks during incidents.

**Playbooks**

* *Check readiness*: poll `/readyz` and recent error logs.
* *Cache refresh*: ask DiscoveryClient to refresh now (by issuing SD reads).
* *Flip policy* to RR temporarily to reduce tail latency.
* *Export* last 10m stats for RCA.

---

## 6) Security & Guardrails

* Require `X-Platform-Token` for admin endpoints and store it only in CI secrets vaults.
* Strip PII from logs; redact tokens in messages.
* Enforce per-agent rate limits (e.g., 10 QPS) and timeouts (`AGENT_REQUEST_TIMEOUT_S`).
* Agents must propagate `X-Request-ID` if provided and log it.

---

## 7) Prompt Templates (for LLM-driven agents)

> Use these as **system** prompts; pass concrete task as the **user** message.

### 7.1 sd-agent (system)

```
You are sd-agent. Operate only the Service Discovery API described below.
Rules: idempotent, retry GET/PUT, no destructive calls without explicit approval.
Emit JSON logs with fields: ts, agent, action, target, trace_id.
```

### 7.2 lb-policy-agent (system)

```
You are lb-policy-agent. Manage per-image policies via LB API.
Validate algorithm ∈ {round_robin, least_conn, weighted_rr}; verify weights are integers ≥1.
If change increases any weight by >50%, request human approval.
Use header X-Platform-Token.
```

### 7.3 health-agent (system)

```
You are health-agent. Poll /readyz for SD and LB. If not-ready, open an incident with context and keep polling until recovery.
```

*(Define similar short system prompts for the remaining agents.)*

---

## 8) Run Locally

* With Compose up, agents can use: `AGENT_SD_BASE=http://localhost:8001`, `AGENT_LB_BASE=http://localhost:8000`.
* Dry-run mode: agents print the HTTP request they would execute without performing it.

---

## 9) Examples

### Set a Weighted-RR policy

```bash
curl -X PUT "$AGENT_LB_BASE/v1/policy/img.video.svc" \
  -H 'Content-Type: application/json' \
  -H "X-Platform-Token: $AGENT_PLATFORM_TOKEN" \
  -d '{"algorithm":"weighted_rr","weights":{"i1":2,"i2":1}}'
```

### Preview routing

```bash
curl -X POST "$AGENT_LB_BASE/v1/route/preview" \
  -H 'Content-Type: application/json' \
  -d '{"service":{"image":"img.video.svc"}}'
```

### Export billing

```bash
curl -X POST "$AGENT_LB_BASE/v1/billing/export?window=1h"
```

---

## 10) Audit Checklist (per agent)

* [ ] Auth header used when required
* [ ] Request/response logged with redactions
* [ ] Retries capped and idempotent
* [ ] HITL required for destructive actions
* [ ] Correlation ID present
* [ ] Unit tests for schema validation

---

## 11) Appendix — Schemas

### PolicyIn

```json
{"algorithm":"round_robin|least_conn|weighted_rr","weights":{"i1":2},"sticky_key":"customer_id?"}
```

### Billing Export (response)

```json
{"generated_at":"2025-08-17T10:00:00Z","window":"1h","schema_version":"1.0","images":[{"image":"img.video.svc","rps_avg":10,"bytes_tx":12345,"req_count":36000,"errors_4xx":3,"errors_5xx":0}]}
```

---

*End of AGENTS.md*
