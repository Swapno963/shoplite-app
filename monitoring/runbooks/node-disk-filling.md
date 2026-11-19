# NodeDiskFilling

A node filesystem is more than 85% full.

## Impact

kubelet eviction, Loki/Tempo/Prometheus ingest failures, and pod restarts.

## Immediate checks

1. Alert labels: `instance` and `mountpoint`.
2. `df -h` on the node, or Grafana node-exporter dashboards.
3. Confirm which workload is writing: Prometheus, Loki, Tempo, or container logs.

## Mitigation

- Expand the PVC for Prometheus, Loki, or Tempo.
- Truncate unused container logs under `/var/log/pods`.
- Cordon the node if eviction has started and drain after disk is recovered.
