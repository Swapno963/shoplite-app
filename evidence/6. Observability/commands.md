## Copy charts to the bastion (from your laptop)

scp -i ~/.ssh/id_ed25519 -r helm monitoring ubuntu@54.251.166.226:~/

scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@54.251.166.226:~/kubeconfig


## 1. Terraform — IAM + subnet tags (from your laptop)

cd ~/Documents/Projects/shoplite-app/terraform

terraform apply

VPC_ID=$(terraform output -raw vpc_id)
echo "$VPC_ID"


## On the bastion

ssh -i ~/.ssh/id_ed25519 ubuntu@54.251.166.226

export KUBECONFIG=/home/ubuntu/kubeconfig

# Paste the VPC id from terraform output:
export VPC_ID='vpc-0e8890ec3b3165c90'

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



## 5. Slack webhook

# values-slack.yaml is gitignored. Copy it to the bastion from your laptop
# (it is created locally, not in git):
#
#   scp -i ~/.ssh/id_ed25519 \
#     helm/observability/values-slack.yaml \
#     ubuntu@54.251.166.226:~/helm/observability/values-slack.yaml
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

