# HighLatency

p95 HTTP latency exceeded 1 second for 5 minutes.

## Impact

The catalog API is slow. Checkout and product pages feel stuck.

## Immediate checks

1. Golden Signals dashboard: latency per route (p50 / p95 / p99).
2. Click an exemplar on the latency series to open the matching Tempo trace.
3. In Tempo, confirm whether time is spent in Django, Redis `LPUSH`, or PostgreSQL.
4. Check `CHAOS_LATENCY_MS` and `CHAOS_SLOW_DB`.

## Mitigation

- Disable chaos latency flags.
- If the trace is stuck on PostgreSQL, inspect slow queries and disk on the postgres volume.
- If Redis is slow, check order queue depth (`QueueBacklog`).
