# HighErrorRate

HTTP 5xx rate exceeded 5% for 5 minutes.

## Impact

Shoppers see failed product or checkout requests. Order creation may drop.

## Immediate checks

1. Open the ShopLite Golden Signals dashboard and confirm the 5xx panel.
2. Filter Loki logs: `{namespace="shoplite", service="catalog-api"} |= "500" | json`.
3. Click `trace_id` on a failing log line to open the Tempo trace.
4. Confirm whether chaos injection is enabled (`CHAOS_ERROR_RATE` in the `shoplite-config` ConfigMap).

## Mitigation

- If chaos flags are set, reset `CHAOS_ERROR_RATE` to `0` and rollout catalog-api.
- If traces show database or Redis failures, check postgres and redis pods in `shoplite`.
- Scale catalog-api if CPU or memory is saturating.
