## Namespace

kubectl create namespace monitoring

## Metrics, dashboards, and alerting (kube-prometheus-stack)

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring/kube-prometheus-stack-values.yaml

## Logs (Loki + Promtail)

helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  --values monitoring/loki-values.yaml

helm upgrade --install promtail grafana/promtail \
  --namespace monitoring \
  --values monitoring/promtail-values.yaml

## Traces (Tempo)

helm upgrade --install tempo grafana/tempo \
  --namespace monitoring \
  --values monitoring/tempo-values.yaml

## Golden Signals dashboard

kubectl create configmap grafana-dashboard-shoplite-golden-signals \
  --from-file=shoplite-golden-signals.json=monitoring/dashboards/shoplite-golden-signals.json \
  --namespace monitoring \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl label configmap grafana-dashboard-shoplite-golden-signals \
  --namespace monitoring \
  grafana_dashboard=1 \
  --overwrite

## Required alerts

kubectl apply -f monitoring/manifests/shoplite-alerts.yaml

## Verify

kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl get daemonset -n monitoring
kubectl get servicemonitor -n shoplite
kubectl get prometheusrule -n monitoring

# Grafana NodePort
kubectl get svc -n monitoring kube-prometheus-stack-grafana

# Confirm Alertmanager routing (Slack webhook)
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d

# Application metrics
kubectl port-forward -n shoplite svc/catalog-api 8080:8080
curl -s http://127.0.0.1:8080/metrics | grep -E 'http_requests_total|http_request_duration_seconds|orders_created_total|order_queue_depth'

kubectl port-forward -n shoplite svc/order-worker 8081:8080
curl -s http://127.0.0.1:8081/metrics | grep -E 'orders_processed_total|order_processing_seconds|order_queue_depth'
