# Chaos Day and Root Cause Analysis

Production troubleshooting on ShopLite. A peer enabled one chaos flag in production GitOps values. I found the fault and recovered using Grafana, Prometheus, Loki, and Tempo. I did not use Git or kubectl env during the investigation.

Screenshots live in `evidence/8. Chaos Day and Root Cause Analysis/screenshots/`. Each one includes dashboard name, time range, and a visible clock.

---

## Chaos flags in the platform

These keys sit on the Helm ConfigMap `shoplite-config` (`applicationConfig` in values). Defaults in `helm/shoplite/values.yaml` are off. Only one flag was on for this exercise.

| Flag | Service | Effect | Signal I used |
|------|---------|--------|----------------|
| `CHAOS_ERROR_RATE` | catalog-api (`POST /orders`) | Probability of HTTP 500 `"Injected failure"` | **HighErrorRate** (5xx > 5% for 5m). Loki: `chaos error injected`. Traces of `/orders` end in 500. |
| `CHAOS_LATENCY_MS` | catalog-api (`GET /products/{id}`) | ~30% of gets sleep that many milliseconds | **HighLatency** if p95 > 1s for 5m. Loki: `chaos latency injected`. Tempo: sleep span on product GET. |
| `CHAOS_SLOW_DB` | order-worker | `SELECT pg_sleep(2)` on DB updates | Worker traces slow on PostgreSQL. Queue may grow → **QueueBacklog** (`order_queue_depth` > 50 for 10m) under load. Loki: `chaos slow db injected`. |
| `CHAOS_MEMORY_LEAK` | order-worker | Keeps 1 KiB blobs per processed order | Memory on `order-worker` climbs. Possible OOM → **PodCrashLooping**. Golden Signals CPU/memory panel. |

---

## Baseline (before the fault)

Production was already healthy:

- Argo CD Application `shoplite-prod` was **Synced / Healthy**
- Grafana hostname:

  ```bash
  kubectl get ingress -n monitoring grafana \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
  ```

- ShopLite Golden Signals dashboard loaded
- Alertmanager / Slack receiving `shoplite.golden-signals` rules
- Production URL from ALB / `envs/prod/values.yaml`
- `k6` (and `hey`) available for load

I captured a baseline Golden Signals screenshot with the timestamp visible: RPS, 5xx rate, p95 latency, queue depth, worker memory — all quiet.

---

## How the fault got into production

I granted the peer write access on **Swapno963/shoplite-gitops** for one hour (GitHub → Settings → Collaborators), then removed it after recovery.

The peer changed only `envs/prod/values.yaml`, enabled exactly one flag under `applicationConfig`, and pushed `main` with a boring commit message so Argo CD would sync production. Catalog-api / order-worker pods rolled because the ConfigMap changed.

One of:

```yaml
applicationConfig:
  DJANGO_DEBUG: "false"
  ALLOWED_HOSTS: "*"
  LOG_LEVEL: "INFO"
  CHAOS_ERROR_RATE: "0.25"      # 25% 500s on POST /orders
  # CHAOS_LATENCY_MS: "3000"    # ~3s sleep on ~30% of GET /products/{id}
  # CHAOS_SLOW_DB: "true"       # 2s pg_sleep in the worker
  # CHAOS_MEMORY_LEAK: "true"   # worker memory growth
```

I waited until `shoplite-prod` was **Synced** before treating the cluster as failed.

---

## Load I ran (15 minutes, ≥ 20 rps)

Chaos on `GET /products/{id}` and `POST /orders` only shows under traffic. `HighErrorRate` and `HighLatency` need `for: 5m`.

`BASE` is the production URL. Paths go through web nginx `/api/`.

**hey**

```bash
# 20 rps for 15 minutes = 18000 requests
hey -z 15m -q 20 -m GET "$BASE/api/products"
```

Second terminal so product-by-id and checkout are hit:

```bash
hey -z 15m -q 10 -m GET "$BASE/api/products/1"

hey -z 15m -q 10 -m POST -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":1}' \
  "$BASE/api/orders"
```

**k6** (what I preferred; ~20 rps mixed)

```javascript
// chaos-load.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  duration: "15m",
  vus: 20,
};

const BASE = __ENV.BASE;

export default function () {
  const list = http.get(`${BASE}/api/products`);
  check(list, { "list 200": (r) => r.status === 200 });

  http.get(`${BASE}/api/products/1`);

  http.post(
    `${BASE}/api/orders`,
    JSON.stringify({ product_id: 1, quantity: 1 }),
    { headers: { "Content-Type": "application/json" } },
  );

  sleep(1);
}
```

```bash
k6 run -e BASE='http://YOUR-ALB-HOST' chaos-load.js
```

Evidence: load-test start (terminal clock) and Golden Signals **Requests per second** above 20. The test ran the full 15 minutes so Alertmanager could fire.

---

## Detection

I used Grafana **Alerting** (and Slack `#shoplite-alerts` when the webhook was installed). Rules are in `helm/observability/templates/shoplite-alerts.yaml`.

| Alert | Condition |
|-------|-----------|
| `HighErrorRate` | 5xx / all HTTP > 5% for 5 minutes |
| `HighLatency` | p95 `http_request_duration_seconds` > 1s for 5 minutes |
| `QueueBacklog` | `order_queue_depth` > 50 for 10 minutes |
| `PodCrashLooping` | container restarts in 10 minutes (rule still labels `namespace="shoplite"`; I also watched worker restarts in Explore with `namespace="shoplite-prod"`) |

Evidence: first firing alert with timestamp. The RCA names that alert and the `for:` / threshold.

---

## Investigation (dashboard → logs → trace)

All of this was in Grafana. I did not open Git or pod env until after the RCA draft.

### Dashboard

Dashboards → **ShopLite Golden Signals** (ConfigMap `grafana-dashboard-shoplite-golden-signals`).

Time range covered the load test (last 30–45 minutes). Full-dashboard screenshot, then the panels:

- **HTTP 5xx error rate** climbing → error injection on `/orders`
- **Request latency per route** p95/p99 up on product GET → latency injection
- **Order queue depth** growing while **orders created** stays high → slow worker / leak / crashes
- **CPU and memory usage per pod** — if the dashboard is pinned to `namespace="shoplite"`, I switched to **Explore → Prometheus** with `namespace="shoplite-prod"`
- **Worker replica count** dropping → OOM / crash

### Prometheus Explore

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / clamp_min(sum(rate(http_requests_total[5m])), 0.001)

histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

max(order_queue_depth)

sum by (pod) (container_memory_working_set_bytes{namespace="shoplite-prod", container!=""})
```

If metrics have a `route` or `path` label, I screenshot which route is red.

### Loki

Explore → Loki.

```logql
{namespace="shoplite-prod"} |= "chaos"
{namespace="shoplite-prod", app="catalog-api"} |= "Injected failure" or "500"
{namespace="shoplite-prod"} |= "chaos error injected"
{namespace="shoplite-prod"} |= "chaos latency injected"
{namespace="shoplite-prod"} |= "chaos slow db injected"
{namespace="shoplite-prod", app="order-worker"} | json | level="ERROR"
```

Evidence: 2–3 log lines with timestamps. If a line has `trace_id`, I copied it. Seeing `chaos` in logs is observability, not looking at Git.

### Tempo

Explore → Tempo → query by trace ID from the log, or an exemplar on the latency/5xx graph.

Trace waterfall:

- 500 on `POST /orders` with almost no DB time → injected API failure
- Long gap on `GET /products/{id}` before DB → injected sleep
- Worker span stuck ~2s on SQL → `pg_sleep`
- Worker dies / missing spans + memory → leak

Hypothesis (one line): which flag, which service — still without confirming in Git.

---

## Evidence pack

In order:

1. Baseline Golden Signals (before)
2. GitHub collaborator invite / time window
3. Load-test command + start timestamp; RPS panel ≥ 20
4. First alert (Alerting or Slack) with timestamp
5. Golden Signals during the incident
6. Loki query + sample lines
7. Tempo trace
8. After recovery: same dashboard with 5xx / latency / queue / memory back to baseline
9. Git revert / Argo CD Synced (after the RCA draft)

---

## Root Cause Analysis

**Title:** ShopLite production incident — Chaos Day  
**Service:** catalog-api / order-worker (as found)  
**Environment:** `shoplite-prod`  
**Authors / date**

### 1. Incident timeline

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

### 2. Detection

- First alert (`HighErrorRate` / `HighLatency` / `QueueBacklog` / `PodCrashLooping`)
- PromQL and `for:` from the rule
- Why this load made it fire (example: 25% injected 500s on `/orders` while other GETs succeeded, so overall 5xx exceeded 5% for five minutes)

### 3. Investigation

- Golden Signals: which panel moved, which route/pod
- Loki: query and a redacted log line (keep `trace_id`)
- Tempo: span names and duration
- Why other flags were less likely (example: memory flat ⇒ not `CHAOS_MEMORY_LEAK`)

### 4. Identified root cause

One paragraph. Example: Production `applicationConfig` enabled `CHAOS_ERROR_RATE`, so `create_order` returned 500 with `"Injected failure"` before persisting an order. Confirmed by Loki `chaos error injected on POST /orders` and Tempo traces with no DB span.

After the RCA I confirmed in Git that `envs/prod/values.yaml` was the change. That confirmation is a short **Verification (post-RCA)** note, not the investigation method.

### 5. Recovery time

`T7 − T3` (alert to healthy dashboard) and `T7 − T6` (revert to Synced).

### 6. Preventive measure

One concrete change, for example:

- Require a pull request + reviewer for `envs/prod/values.yaml`
- Grafana alert on Loki `{namespace="shoplite-prod"} |= "chaos"`
- CI / Helm schema so `CHAOS_*` cannot be non-default in prod

---

## Recovery

After the RCA draft I reverted through Git. No `helm rollback` or `kubectl set env`.

```bash
cd shoplite-gitops
git fetch origin
git log --oneline -5
git revert HEAD --no-edit   # or the peer commit SHA
git push origin main
```

`shoplite-prod` has automated sync + self-heal, prune false. A values-only revert is enough:

```bash
kubectl -n argocd get application shoplite-prod -w
```

Pods rolled when the ConfigMap changed. I kept light load for a few minutes.

Grafana after recovery (same Golden Signals dashboard, time range covering incident and after revert):

- 5xx near 0, p95 under 1s, queue draining, worker memory flat
- Alert state **Normal** / resolved

I removed the peer’s write access on `shoplite-gitops`.

---

## What matched which flag

| What I saw | Flag |
|------------|------|
| 5xx panel + Loki `chaos error injected` + Tempo 500 on POST `/orders` | `CHAOS_ERROR_RATE` |
| p95 up on product GET + Loki `chaos latency injected` | `CHAOS_LATENCY_MS` |
| Queue depth up, worker traces ~2s SQL, Loki `chaos slow db` | `CHAOS_SLOW_DB` |
| Worker RSS up or OOM restarts, Loki otherwise quiet | `CHAOS_MEMORY_LEAK` |

---

## Notes from the run

- Production namespace is **`shoplite-prod`**. Some dashboard queries and `PodCrashLooping` still hardcode `namespace="shoplite"` (old Helm install). Empty panels meant I needed Explore with `shoplite-prod`.
- `HighErrorRate` / `HighLatency` need sustained traffic for 5 minutes. A short curl does not fire them.
- `CHAOS_LATENCY_MS` only applies to **GET product by id**, not list products, so that URL has to be in the load mix.
- `CHAOS_ERROR_RATE` only applies to **POST /orders**.
- Worker flags need orders that succeed (`SLOW_DB`, `MEMORY_LEAK`). If the peer picked error-rate, the worker can look fine.
- If `shoplite-prod` stayed OutOfSync, it was repo credentials, not Helm.
