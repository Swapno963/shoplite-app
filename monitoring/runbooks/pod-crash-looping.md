# PodCrashLooping

A ShopLite pod restarted at least once in the last 10 minutes.

## Impact

Drop in replicas, 5xx errors, or a growing order queue.

## Immediate checks

1. `kubectl get pods -n shoplite`
2. `kubectl describe pod <pod> -n shoplite`
3. `kubectl logs <pod> -n shoplite --previous`
4. Loki: `{namespace="shoplite"} | json | level="ERROR"`

## Mitigation

- OOMKilled: raise memory limits or disable `CHAOS_MEMORY_LEAK`.
- Probe failures: confirm `/healthz` and `/readyz` on catalog-api, and that postgres/redis are Ready.
- Image pull errors: confirm the node ECR credential provider and the image tag.
