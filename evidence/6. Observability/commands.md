## Install kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update


## A namespace for monitoring resources:
kubectl create namespace monitoring



## Install the monitoring stack:
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring-values.yaml




## Verify Monitoring Stack Installation
kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl get daemonset -n monitoring


## Get the NodePort for Grafana service:
kubectl get svc -n monitoring kube-prometheus-stack-grafana


## Inspect the input config (easiest way to confirm your Slack block made it in):
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d

## Inspect the rendered config (ground truth — what Alertmanager is running with):
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager-generated \
  -o jsonpath='{.data.alertmanager\.yaml\.gz}' | base64 -d | gunzip







# Create Custom PrometheusRule Resources
kubectl apply -f custom-alerts.yaml

# Add a Real Custom Scrape Target


Stage 1 done
---------
Hadolint
helm lint
yamllint

Stage 2 done
---------
Unit Test
Integration Test

Stage 3 done
---------
Build Images

Stage 4 done
---------
Trivy Scan
Grype Scan (optional)

Stage 5
---------
Push Images

Stage 6
---------
helm template
helm upgrade --install

Stage 7
---------
Post Deployment Smoke Test