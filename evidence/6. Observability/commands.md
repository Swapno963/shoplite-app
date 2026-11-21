## Copy charts to the bastion (from your laptop)

scp -i ~/.ssh/id_ed25519 -r helm monitoring ubuntu@18.139.227.140:~/

scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@18.139.227.140:~/kubeconfig


## 1. Terraform — IAM + subnet tags (from your laptop)

cd ~/Documents/Projects/shoplite-app/terraform

terraform apply

VPC_ID=$(terraform output -raw vpc_id)
echo "$VPC_ID"


## On the bastion

ssh -i ~/.ssh/id_ed25519 ubuntu@18.139.227.140

export KUBECONFIG=/home/ubuntu/kubeconfig

# Paste the VPC id from terraform output:
export VPC_ID='vpc-04613ee77f5690a53'

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

# "release: not found" is OK on a fresh cluster. PrometheusRule CRDs
# do not exist until the umbrella is installed — ignore that error too.

helm uninstall promtail -n monitoring || true
helm uninstall tempo -n monitoring || true
helm uninstall loki -n monitoring || true
helm uninstall kube-prometheus-stack -n monitoring || true

kubectl delete ingress grafana -n monitoring --ignore-not-found
kubectl delete configmap grafana-dashboard-shoplite-golden-signals -n monitoring --ignore-not-found
kubectl delete prometheusrule shoplite-alerts -n monitoring --ignore-not-found || true


## 5. Slack webhook

# values-slack.yaml is gitignored. Copy it to the bastion from your laptop
# (it is created locally, not in git):
#
#   scp -i ~/.ssh/id_ed25519 \
#     helm/observability/values-slack.yaml \
#     ubuntu@18.139.227.140:~/helm/observability/values-slack.yaml
#
# Template: helm/observability/values-slack.yaml.example
# Channel: #shoplite-alerts (must match the Incoming Webhook's channel)

# Standalone kube-prometheus-stack (not the umbrella):
#   helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
#     -n monitoring \
#     -f ~/monitoring/kube-prometheus-stack-values.yaml \
#     -f ~/monitoring/values-slack.yaml


## 6. Observability umbrella
# Live stack is helm/observability (this install). The monitoring/ folder is
# standalone chart values + runbooks; do not helm-install those on top of the umbrella.
# Prometheus + Grafana + Alertmanager + Loki + Promtail + Tempo
# Golden Signals dashboard + five PrometheusRules
# Grafana Ingress (ALB, HTTP, IP allowlist)

# Optional: lock Grafana to your public IP
#   --set grafanaInboundCidrs=1.2.3.4/32

cd /home/ubuntu/helm/observability

# Confirm Chart.yaml pins grafana/tempo 1.21.1 (1.21.2 was never published).
grep -A1 'name: tempo' Chart.yaml

# Do NOT add charts/*.tgz to .helmignore. helm upgrade --install . applies
# .helmignore and will then report the four subcharts as missing.

helm repo update
helm dependency update

ls charts/
# expect:
#   kube-prometheus-stack-77.12.0.tgz  loki-6.29.0.tgz
#   promtail-6.17.1.tgz                tempo-1.21.1.tgz

# First install pulls images and creates PVCs; --wait can take most of 20m.
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
kubectl get svc -n monitoring grafana
# Grafana Service must be NodePort 30300 (ALB instance targets cannot use ClusterIP).
# Do not use 30080 — that NodePort is ShopLite ingress-nginx.

kubectl get ingress -n monitoring grafana
kubectl get prometheusrule -n monitoring


## 7. ShopLite ServiceMonitors (CRDs exist after step 6)

helm upgrade shoplite /home/ubuntu/helm/shoplite \
  -f /home/ubuntu/helm/shoplite/values-prod.yaml \
  --namespace shoplite

kubectl get servicemonitor -n shoplite


## 8. Open Grafana

kubectl get ingress -n monitoring grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'

# Must be HTTP (there is no 443 listener / ACM). Chrome HTTPS-only mode
# times out on 443 (SG drops; looks like ERR_CONNECTION_TIMED_OUT).
#   http://<that-hostname>/login
# Login: admin / admin
# Dashboards → ShopLite — Golden Signals
#
# AWS console: listener default "fixed 404" is normal for AWS Load Balancer
# Controller. Real routing is the extra listener rules (path / → Grafana).
#
# Prometheus and Alertmanager are ClusterIP only (no public URL).

# If the bastion curl is 200 but your laptop browser times out:
# the ALB is healthy; your home IP is not allowed (or the browser used IPv6/HTTPS).
# AWS console → that ALB → Security → inbound must include TCP 80 from 0.0.0.0/0
# (or your public IP /32). A rule of only 10.0.0.0/16 explains bastion-ok / laptop-timeout.
#
# On the bastion, force the LBC-managed SG:
kubectl annotate ingress grafana -n monitoring --overwrite \
  alb.ingress.kubernetes.io/inbound-cidrs='0.0.0.0/0' \
  alb.ingress.kubernetes.io/ip-address-type=ipv4
#
# From your laptop (not the bastion):
#   curl -4 -sI http://<grafana-alb-hostname>/login
#
# Workaround (laptop → bastion → Grafana Service), from your laptop:
#   ssh -i ~/.ssh/id_ed25519 -L 3000:127.0.0.1:3000 ubuntu@18.139.227.140
# then on the bastion:
#   kubectl -n monitoring port-forward svc/grafana 3000:80
# Browser: http://127.0.0.1:3000/login


## 9. Check application metrics

# port-forward is a long-running process. Keep it open, then curl from a
# second SSH session. If you Ctrl+C first, curl hits nothing and prints empty.
#
# One session (no port-forward): scrape from inside the pods.

kubectl -n shoplite exec deploy/catalog-api -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/metrics').read().decode())" \
  | grep -E 'http_requests_total|http_request_duration_seconds|orders_created_total|order_queue_depth'

kubectl -n shoplite exec deploy/order-worker -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/metrics').read().decode())" \
  | grep -E 'orders_processed_total|order_processing_seconds|order_queue_depth'

# Two-session alternative:
#   kubectl -n shoplite port-forward svc/catalog-api 8080:8080
#   curl -s http://127.0.0.1:8080/metrics | grep -E 'http_requests_total|orders_created_total'























<!-- to get graphana address -->
After Grafana’s Ingress has an ADDRESS:

kubectl get ingress -n monitoring grafana \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'


<!-- If the command prints nothing, ADDRESS is still empty (ClusterIP issue, or the ALB is still creating). Then: -->
kubectl get ingress -n monitoring grafana
kubectl describe ingress -n monitoring grafana
