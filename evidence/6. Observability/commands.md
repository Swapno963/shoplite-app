# Observability stack (Grafana / Prometheus / Loki / Tempo)

Laptop first, then the bastion. Use the current bastion IP from Terraform. Last time I used `13.213.41.145`.

## Copy files up

```bash
scp -i ~/.ssh/id_ed25519 -r helm monitoring ubuntu@13.213.41.145:~/

scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@13.213.41.145:~/kubeconfig
```

`values-slack.yaml` is gitignored. Copy it yourself:

```bash
scp -i ~/.ssh/id_ed25519 \
  helm/observability/values-slack.yaml \
  ubuntu@13.213.41.145:~/helm/observability/values-slack.yaml
```

Template: `helm/observability/values-slack.yaml.example`. Slack channel I used: `#shoplite-alerts`.

## IAM / VPC id (laptop)

```bash
cd ~/Documents/Projects/shoplite-app/terraform
terraform apply
VPC_ID=$(terraform output -raw vpc_id)
echo "$VPC_ID"
```

## On the bastion

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.213.41.145
export KUBECONFIG=/home/ubuntu/kubeconfig
export VPC_ID='vpc-0e8890ec3b3165c90'   # paste yours
kubectl get nodes
```

Helm repos:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

## AWS Load Balancer Controller

Grafana gets its own ALB (`ingressClass: alb`). ShopLite HTTP still goes through ingress-nginx.

```bash
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --values /home/ubuntu/helm/aws-load-balancer-controller/values.yaml \
  --set vpcId="$VPC_ID" \
  --wait --timeout 5m

kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl get ingressclass alb
```

## Observability umbrella

Live install is `helm/observability`. Don't also helm-install the files under `monitoring/` on top of it.

Pin: Tempo in `Chart.yaml` is **1.21.1** (1.21.2 was never published). Do **not** put `charts/*.tgz` in `.helmignore` or `helm upgrade --install .` will say the subcharts are missing.

```bash
cd /home/ubuntu/helm/observability
grep -A1 'name: tempo' Chart.yaml

helm repo update
helm dependency update
ls charts/
# kube-prometheus-stack-*.tgz  loki-*.tgz  promtail-*.tgz  tempo-1.21.1.tgz
```

First install pulls images and creates PVCs. `--wait` can sit there for most of 20 minutes.

Optional: lock Grafana to your IP with `--set grafanaInboundCidrs=1.2.3.4/32`.

```bash
helm upgrade --install observability . \
  --namespace monitoring \
  --create-namespace \
  -f /home/ubuntu/helm/observability/values.yaml \
  -f /home/ubuntu/helm/observability/values-slack.yaml \
  --wait --timeout 20m
```

Webhook actually in the secret (should not say `REPLACE_ME`):

```bash
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d

kubectl get pods -n monitoring
kubectl get svc -n monitoring grafana
kubectl get ingress -n monitoring grafana
kubectl get prometheusrule -n monitoring
```

Grafana Service is NodePort **30300**. Don't steal **30080** — that is ShopLite ingress-nginx.

## ShopLite ServiceMonitors

Only after the monitoring CRDs exist. If the app is already on Argo CD, skip this Helm upgrade and let GitOps own ShopLite.

```bash
helm upgrade shoplite /home/ubuntu/helm/shoplite \
  -f /home/ubuntu/helm/shoplite/values-prod.yaml \
  --namespace shoplite

kubectl get servicemonitor -n shoplite
```

## Open Grafana

```bash
kubectl get ingress -n monitoring grafana \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
```

Browser: `http://<that-hostname>/`

Before you `terraform destroy`, delete the Grafana Ingress so the Kubernetes ALB goes away:

```bash
kubectl delete ingress grafana -n monitoring --wait=true
```
