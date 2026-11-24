# Chaos Day and Root Cause Analysis

Production troubleshooting exercise. A peer (or instructor) secretly enables **one** ShopLite chaos flag in **production GitOps values**. You find and recover from the fault using **Grafana, Prometheus, Loki, and Tempo only**. You do **not** inspect the Git diff or pod environment variables until the RCA is written.

Marks: chaos exercise 3, RCA 5, recovery 2. The RCA is graded on reasoning and evidence, not speed.

---

## Question 1 — chaos flags (what the peer may enable)

These keys live on the Helm ConfigMap `shoplite-config` (`applicationConfig` in values). Defaults in `helm/shoplite/values.yaml` are off.

| Flag | Service | Effect | What you should see |
|------|---------|--------|---------------------|
| `CHAOS_ERROR_RATE` | catalog-api (`POST /orders`) | Probability of HTTP 500 `"Injected failure"` | **HighErrorRate** (5xx > 5% for 5m). Loki: `chaos error injected`. Traces of `/orders` end in 500. |
| `CHAOS_LATENCY_MS` | catalog-api (`GET /products/{id}`) | ~30% of gets sleep that many milliseconds | **HighLatency** if p95 > 1s for 5m (set the flag high enough, e.g. `3000`). Loki: `chaos latency injected`. Tempo: sleep span on product GET. |
| `CHAOS_SLOW_DB` | order-worker | `SELECT pg_sleep(2)` on DB updates | Worker traces slow on PostgreSQL. Queue may grow → **QueueBacklog** (`order_queue_depth` > 50 for 10m) under load. Loki: `chaos slow db injected`. |
| `CHAOS_MEMORY_LEAK` | order-worker | Keeps 1 KiB blobs per processed order | Memory on `order-worker` climbs. Possible OOM → **PodCrashLooping**. Golden Signals: CPU/memory panel (filter namespace). |

Only **one** flag is enabled for the exercise.

---

## 0. Before the exercise (you)

Production must already be healthy:

- Argo CD Application `shoplite-prod` is **Synced / Healthy**
- Grafana reachable:

  ```bash
  kubectl get ingress -n monitoring grafana \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
  ```

- ShopLite Golden Signals dashboard is loaded
- Alertmanager / Slack (if configured) is receiving `shoplite.golden-signals` rules
- You know the **production URL** (ALB or `shoplite.example.com` from `envs/prod/values.yaml`)
- `k6` or `hey` installed on your laptop (or a jump host)

Record a **baseline** screenshot (timestamp visible): Golden Signals RPS, 5xx rate, p95 latency, queue depth, worker memory — all quiet.

Create an evidence folder on your machine, for example `evidence/8. Chaos Day and Root Cause Analysis/screenshots/`. Every screenshot: dashboard name, time range, and clock/timestamp.

**Rules until the RCA draft is done:**

- Do **not** `git log` / `git diff` / `git show` on `shoplite-gitops`
- Do **not** `kubectl describe` / `kubectl exec` / `kubectl get cm shoplite-config -o yaml` / `env` on pods
- You **may** use Grafana, Prometheus (Explore), Loki, Tempo, Alertmanager
- You **may** run the load generator (that is part of the procedure)

---

## 8.1 Exercise procedure

### Step 1 — Grant the peer write access (1 hour)

On GitHub: **Swapno963/shoplite-gitops** → Settings → Collaborators → add the peer with **write**. Remove access after the hour (or after recovery).

Tell them:

- Change **only** `envs/prod/values.yaml`
- Enable **exactly one** flag under `applicationConfig`
- Commit message must look boring (`Tune production logging`, `Align prod timeouts`, etc.)
- Push `main` (Argo CD auto-syncs production)

You leave the room / do not watch GitHub.

### Step 2 — Peer injects the fault (peer only)

Do **not** read this during the investigation. This is for the peer or for you after the RCA.

In `shoplite-gitops/envs/prod/values.yaml`, under `applicationConfig`, add **one** of:

```yaml
applicationConfig:
  DJANGO_DEBUG: "false"
  ALLOWED_HOSTS: "*"
  LOG_LEVEL: "INFO"
  CHAOS_ERROR_RATE: "0.25"      # option A — 25% 500s on POST /orders
  # CHAOS_LATENCY_MS: "3000"    # option B — ~3s sleep on ~30% of GET /products/{id}
  # CHAOS_SLOW_DB: "true"       # option C — 2s pg_sleep in the worker
  # CHAOS_MEMORY_LEAK: "true"   # option D — worker memory growth
```

```bash
cd shoplite-gitops
git add envs/prod/values.yaml
git commit -m "Tune production logging"
git push origin main
```

Wait until Argo CD Application `shoplite-prod` is **Synced** (UI or `kubectl -n argocd get application shoplite-prod`). Catalog-api / order-worker pods roll because the ConfigMap changed.

### Step 3 — You start a 15-minute load test (≥ 20 rps)

Chaos on `GET /products/{id}` and `POST /orders` only shows under traffic. Alerts need minutes of rate (`HighErrorRate` and `HighLatency` are `for: 5m`).

Set `BASE` to the production URL (ALB `http://...elb.amazonaws.com` or the Ingress host). Paths go through web nginx `/api/`.

**hey** (simple):

```bash
# 20 rps for 15 minutes = 18000 requests
hey -z 15m -q 20 -m GET "$BASE/api/products"
```

Run a **second** terminal so orders and product-by-id are hit (needed for error-rate and latency flags):

```bash
# product detail (latency chaos)
hey -z 15m -q 10 -m GET "$BASE/api/products/1"

# checkout (error-rate chaos) — need a real product id from GET /api/products
hey -z 15m -q 10 -m POST -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":1}' \
  "$BASE/api/orders"
```

**k6** (preferred; ~20 rps mixed):

```javascript
// chaos-load.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  duration: "15m",
  vus: 20,
};

const BASE = __ENV.BASE; // e.g. http://shoplite-alb-xxxx.ap-southeast-1.elb.amazonaws.com

export default function () {
  const list = http.get(`${BASE}/api/products`);
  check(list, { "list 200": (r) => r.status === 200 });

  http.get(`${BASE}/api/products/1`);

  http.post(
    `${BASE}/api/orders`,
    JSON.stringify({ product_id: 1, quantity: 1 }),
    { headers: { "Content-Type": "application/json" } },
  );

  sleep(1); // 20 VUs * ~1 req cycle/s ≈ 20 rps
}
```

```bash
k6 run -e BASE='http://YOUR-ALB-HOST' chaos-load.js
```

Screenshot: load-test start time (terminal clock) and Golden Signals **Requests per second** rising above 20.

Keep the test running the full 15 minutes so Alertmanager can fire.

### Step 4 — Detect (Alertmanager / Slack / Grafana)

Open Grafana → **Alerting** (or Slack `#shoplite-alerts` if the webhook is installed).

Expected alerts (from `helm/observability/templates/shoplite-alerts.yaml`):

| Alert | When |
|-------|------|
| `HighErrorRate` | 5xx / all HTTP > 5% for 5 minutes |
| `HighLatency` | p95 `http_request_duration_seconds` > 1s for 5 minutes |
| `QueueBacklog` | `order_queue_depth` > 50 for 10 minutes |
| `PodCrashLooping` | container restarts in 10 minutes (rule still labels `namespace="shoplite"`; also watch worker restarts in Explore with `namespace="shoplite-prod"`) |

Screenshot the **first firing alert** with timestamp. In the RCA, name that alert and quote the `for:` / threshold so you can explain **why** it fired.

### Step 5 — Investigate (dashboard → logs → trace)

Stay in Grafana. Do **not** open Git or kubectl env.

**A. Dashboard**

Dashboards → **ShopLite Golden Signals** (ConfigMap `grafana-dashboard-shoplite-golden-signals`).

1. Set the time range to cover the load test (last 30–45 minutes).
2. Screenshot the full dashboard.
3. Read the panels:
   - **HTTP 5xx error rate** climbing → error injection on `/orders`
   - **Request latency per route** p95/p99 up on product GET → latency injection
   - **Order queue depth** growing while **orders created** stays high → slow worker / leak / crashes
   - **CPU and memory usage per pod** — if the dashboard is pinned to `namespace="shoplite"`, switch to **Explore → Prometheus** and re-run with `namespace="shoplite-prod"`
   - **Worker replica count** dropping → OOM / crash

**B. Prometheus Explore** (copy from the dashboard, add namespace if needed)

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / clamp_min(sum(rate(http_requests_total[5m])), 0.001)

histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

max(order_queue_depth)

sum by (pod) (container_memory_working_set_bytes{namespace="shoplite-prod", container!=""})
```

If metrics have a `route` or `path` label, screenshot which route is red.

**C. Loki**

Explore → Loki. Prefer JSON if the app emits it.

```logql
{namespace="shoplite-prod"} |= "chaos"
{namespace="shoplite-prod", app="catalog-api"} |= "Injected failure" or "500"
{namespace="shoplite-prod"} |= "chaos error injected"
{namespace="shoplite-prod"} |= "chaos latency injected"
{namespace="shoplite-prod"} |= "chaos slow db injected"
{namespace="shoplite-prod", app="order-worker"} | json | level="ERROR"
```

Screenshot 2–3 log lines with **timestamps**. If a line has `trace_id`, copy it.

You are allowed to see the word `chaos` in **logs**. That is observability, not Git or env.

**D. Tempo**

Explore → Tempo → **Query by Trace ID** from the log, or click an **exemplar** on the latency/5xx Prometheus graph.

Screenshot the trace waterfall:

- 500 on `POST /orders` with almost no DB time → injected API failure
- Long gap on `GET /products/{id}` before DB → injected sleep
- Worker span stuck ~2s on SQL → `pg_sleep`
- Worker dies / missing spans + memory → leak

Write a one-line hypothesis: *which flag, which service*. Still do **not** confirm via Git.

### Step 6 — Write the RCA first

Draft the 1–2 page RCA (section 8.2(b) template below) using only screenshots and timestamps from steps 3–5. Then recover.

---

## 8.2 Assessment

### (a) Chaos exercise — evidence pack

Keep, in order:

1. Baseline Golden Signals (before)
2. GitHub collaborator invite / time window (optional screenshot)
3. Load-test command + start timestamp; RPS panel ≥ 20
4. First alert (Alerting or Slack) with timestamp
5. Golden Signals during the incident
6. Loki query + sample lines
7. Tempo trace
8. After recovery: same dashboard showing 5xx/latency/queue/memory back to baseline
9. Git revert / Argo CD Synced (this one **after** the RCA draft)

### (b) Root Cause Analysis — 1–2 pages

Use this structure.

**Title:** ShopLite production incident — Chaos Day  
**Service:** catalog-api / order-worker (as found)  
**Environment:** `shoplite-prod`  
**Authors / date**

**1. Incident timeline** (use screenshot clocks)

| Time (UTC+6) | Event |
|--------------|--------|
| T0 | Baseline healthy; load test not started |
| T1 | Load test started (≥ 20 rps) |
| T2 | First dashboard anomaly (panel + what changed) |
| T3 | First alert `AlertName` firing (`for` duration elapsed) |
| T4 | Loki/Tempo confirmed hypothesis |
| T5 | RCA drafted |
| T6 | Git revert pushed |
| T7 | Argo CD Synced; dashboard recovered |

**2. Detection**

- Name the first alert (`HighErrorRate` / `HighLatency` / `QueueBacklog` / `PodCrashLooping`).
- Restate the PromQL and `for:` from the rule (see table in step 4).
- Explain why **this** load made it fire (example: 25% injected 500s on `/orders` while other GETs succeeded, so overall 5xx exceeded 5% for five minutes).

**3. Investigation** (dashboard → logs → trace)

- Golden Signals: which panel moved, which route/pod.
- Loki: exact query and a redacted log line (keep `trace_id`).
- Tempo: span names and duration; where time or the error sits.
- Why other flags are **less** likely (example: memory flat ⇒ not `CHAOS_MEMORY_LEAK`).

**4. Identified root cause**

One paragraph. Example: *Production `applicationConfig` enabled `CHAOS_ERROR_RATE`, so `create_order` returned 500 with `"Injected failure"` before persisting an order. Confirmed by Loki `chaos error injected on POST /orders` and Tempo traces with no DB span.*

After the RCA is written you may confirm in Git that `envs/prod/values.yaml` was the change. Put that confirmation in a short **Verification (post-RCA)** note, not as the investigation method.

**5. Recovery time**

`T7 − T3` (alert to healthy dashboard) and `T7 − T6` (revert to Synced). State both.

**6. One preventive measure** (pick one, make it concrete)

Examples:

- Require a pull request + reviewer for `envs/prod/values.yaml`; do not push chaos flags to `main` without a label
- Add a Grafana alert on Loki `{namespace="shoplite-prod"} |= "chaos"` so injection is explicit
- Gate production values so `CHAOS_*` cannot be non-default in prod (`helm` schema / CI check)

### (c) Recovery — revert through Git, show Grafana

**After** the RCA draft:

```bash
cd shoplite-gitops
git fetch origin
git log --oneline -5   # now allowed
git revert HEAD --no-edit   # or revert the peer commit SHA
git push origin main
```

If you are not the one who pushed, revert **that** commit:

```bash
git revert <peer-commit-sha> --no-edit
git push origin main
```

`shoplite-prod` has automated sync + self-heal, **prune false**. A values-only revert is enough; wait for Synced:

```bash
kubectl -n argocd get application shoplite-prod -w
```

Do **not** `helm rollback` or `kubectl set env`. Recovery must be Git → Argo CD.

Pods roll when the ConfigMap changes. Continue light load for a few minutes.

**Demonstrate recovery on Grafana**

- Same Golden Signals dashboard, time range including incident **and** after revert
- 5xx rate back near 0, p95 under 1s, queue draining, worker memory flat
- Alerting: alert state **Normal** / resolved
- Screenshot this for (c)

Remove the peer’s write access on `shoplite-gitops`.

---

## Symptom → likely flag (cheat sheet after RCA)

| You saw | Likely flag |
|---------|-------------|
| 5xx panel + Loki `chaos error injected` + Tempo 500 on POST `/orders` | `CHAOS_ERROR_RATE` |
| p95 up on product GET + Loki `chaos latency injected` | `CHAOS_LATENCY_MS` |
| Queue depth up, worker traces ~2s SQL, Loki `chaos slow db` | `CHAOS_SLOW_DB` |
| Worker RSS up or OOM restarts, Loki otherwise quiet | `CHAOS_MEMORY_LEAK` |

---

## Notes

- Production namespace is **`shoplite-prod`**. Some dashboard queries and `PodCrashLooping` still hardcode `namespace="shoplite"` (the old Helm install). Use Explore and set `shoplite-prod` if panels look empty.
- `HighErrorRate` / `HighLatency` need **sustained** traffic for 5 minutes. A short curl will not fire alerts.
- `CHAOS_LATENCY_MS` only applies to **GET product by id**, not list products. Mix that URL into the load test.
- `CHAOS_ERROR_RATE` only applies to **POST /orders**.
- Worker flags need **orders that succeed** so the worker actually runs (`SLOW_DB`, `MEMORY_LEAK`). If the peer picked error-rate, the worker may look fine.
- Argo CD must be allowed to auto-sync prod; if the Application is OutOfSync and stuck, check repo credentials, not Helm.
