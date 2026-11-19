## Copy charts to the bastion (from your laptop)

scp -i ~/.ssh/id_ed25519 -r helm monitoring ubuntu@13.213.44.151:~/

scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@13.213.44.151:~/kubeconfig


## 1. Terraform — IAM + subnet tags (from your laptop)

cd ~/Documents/Projects/shoplite-app/terraform

terraform apply

VPC_ID=$(terraform output -raw vpc_id)
echo "$VPC_ID"


## On the bastion

ssh -i ~/.ssh/id_ed25519 ubuntu@13.213.44.151

export KUBECONFIG=/home/ubuntu/kubeconfig

# Paste the VPC id from terraform output:
export VPC_ID='vpc-xxxxxxxx'

kubectl get nodes


## 2. Helm repos

helm repo add eks https://aws.github.io/eks-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update


## 3. AWS Load Balancer Controller

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --values /home/ubuntu/helm/aws-load-balancer-controller/values.yaml \
  --set vpcId="$VPC_ID" \
  --wait --timeout 5m

kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl get ingressclass alb


## 4. Remove the old per-chart monitoring installs (if they exist)

helm uninstall promtail -n monitoring
helm uninstall tempo -n monitoring
helm uninstall loki -n monitoring
helm uninstall kube-prometheus-stack -n monitoring

kubectl delete ingress grafana -n monitoring --ignore-not-found
kubectl delete configmap grafana-dashboard-shoplite-golden-signals -n monitoring --ignore-not-found
kubectl delete prometheusrule shoplite-alerts -n monitoring --ignore-not-found


## 5. Slack webhook

# values-slack.yaml is gitignored. Copy it to the bastion from your laptop
# (it is created locally, not in git):
#
#   scp -i ~/.ssh/id_ed25519 \
#     helm/observability/values-slack.yaml \
#     ubuntu@13.213.44.151:~/helm/observability/values-slack.yaml
#
# Template: helm/observability/values-slack.yaml.example
# Channel: #shoplite-alerts (must match the Incoming Webhook's channel)

# Standalone kube-prometheus-stack (not the umbrella):
#   helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
#     -n monitoring \
#     -f ~/monitoring/kube-prometheus-stack-values.yaml \
#     -f ~/monitoring/values-slack.yaml


## 6. Observability umbrella
# Prometheus + Grafana + Alertmanager + Loki + Promtail + Tempo
# Golden Signals dashboard + five PrometheusRules
# Grafana Ingress (ALB, HTTP, IP allowlist)

# Optional: lock Grafana to your public IP
#   --set grafanaInboundCidrs=1.2.3.4/32

cd /home/ubuntu/helm/observability
helm dependency update

helm upgrade --install observability . \
  --namespace monitoring \
  --create-namespace \
  -f /home/ubuntu/helm/observability/values.yaml \
  -f /home/ubuntu/helm/observability/values-slack.yaml \
  --wait --timeout 20m

# Confirm the webhook landed (should not show REPLACE_ME or YOUR_SLACK_WEBHOOK_URL)
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d


kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl get ingress -n monitoring grafana
kubectl get prometheusrule -n monitoring


## 7. ShopLite ServiceMonitors (CRDs exist after step 6)

helm upgrade shoplite /home/ubuntu/helm/shoplite \
  -f /home/ubuntu/helm/shoplite/values-prod.yaml \
  --namespace shoplite

kubectl get servicemonitor -n shoplite


## 8. Open Grafana

kubectl get ingress -n monitoring grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'

# Browser (from an IP allowed by grafanaInboundCidrs):
#   http://<that-hostname>/
# Login: admin / admin
# Dashboards → ShopLite — Golden Signals
#
# Prometheus and Alertmanager are ClusterIP only (no public URL).


## 9. Check application metrics

kubectl -n shoplite port-forward svc/catalog-api 8080:8080
# other terminal:
curl -s http://127.0.0.1:8080/metrics | grep -E 'http_requests_total|http_request_duration_seconds|orders_created_total|order_queue_depth'

kubectl -n shoplite port-forward svc/order-worker 8081:8080
curl -s http://127.0.0.1:8081/metrics | grep -E 'orders_processed_total|order_processing_seconds|order_queue_depth'
