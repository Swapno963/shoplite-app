# QueueBacklog

`order_queue_depth` stayed above 50 for 10 minutes.

## Impact

Orders are accepted by the API but not completed. Shoppers see pending status.

## Immediate checks

1. Golden Signals: queue depth vs worker replica count vs orders created/processed.
2. `kubectl get pods -n shoplite -l app=order-worker`
3. Loki: `{namespace="shoplite", service="order-worker"} | json`
4. Follow a `trace_id` from an `enqueued order` API log through the worker `process_order` span.

## Mitigation

- Scale the order-worker deployment (HPA should already target CPU).
- If workers are crash-looping, follow the PodCrashLooping runbook.
- If workers are healthy but idle, confirm they share `ORDERS_QUEUE` and `REDIS_URL` with the API.
