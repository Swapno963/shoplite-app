# Helm on the bastion (first ShopLite install)

Later I moved the app to Argo CD. This is still how I installed kubectl/Helm on the bastion and how I first shipped ShopLite with Helm. Ingress-nginx is still a Helm add-on.

IPs change after every Terraform apply. Use the current bastion from `terraform output`.

## Copy charts + kubeconfig from the laptop

```bash
scp -i ~/.ssh/id_ed25519 -r helm ubuntu@13.213.1.147:~/

scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@13.213.1.147:~/
```

SSH in:

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.213.1.147
```

## kubectl + Helm on the bastion

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
kubectl version --client

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

export KUBECONFIG=~/kubeconfig
kubectl get nodes
kubectl get pods -A
kubectl config view --minify
```

Chart checks (from `~/helm/shoplite` if you are linting the app chart):

```bash
cd ~/helm/shoplite
helm dependency update .
helm lint .
```

## Secrets, then Helm install (old path)

```bash
export POSTGRES_PASSWORD='my-db-password'
export DJANGO_SECRET_KEY='my-django-secret'
export REDIS_PASSWORD='my-redis-secret'

kubectl create namespace shoplite

kubectl create secret generic shoplite-secret -n shoplite \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD"

helm upgrade --install shoplite . \
  -f values-prod.yaml \
  --namespace shoplite
```

Today Argo CD owns `shoplite-dev` / `shoplite-prod` instead of this `shoplite` namespace. Don't run this install if GitOps is already live.

## ingress-nginx (still used)

ALB forwards to worker NodePort **30080**. ShopLite services are ClusterIP, so nginx needs that port.

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values ~/helm/ingress-nginx-values.yaml \
  --wait

kubectl get svc -n ingress-nginx
kubectl get ingress -n shoplite
```

From the bastion, hit a worker private IP:

```bash
curl -I http://<worker-private-ip>:30080/
```

Browser: Terraform `alb_dns_name`, for example:

```text
http://shoplite-alb-192242708.ap-southeast-1.elb.amazonaws.com/
```

## Debugging I actually used

```bash
kubectl get all -n shoplite

kubectl describe pod -n shoplite -l app=catalog-api
kubectl logs -n shoplite deploy/catalog-api --tail=100
kubectl logs -n shoplite deploy/order-worker --tail=100
kubectl logs -n shoplite deploy/web --tail=50

kubectl rollout restart deployment catalog-api web order-worker -n shoplite
kubectl get pods -n shoplite -w
```

Helm diff before an upgrade:

```bash
helm plugin install https://github.com/databus23/helm-diff

helm diff upgrade shoplite . \
  -f values-prod.yaml \
  --namespace shoplite
```

## ECR / node IAM (when pulls fail)

```bash
aws sts get-caller-identity
aws ecr get-login-password --region ap-southeast-1 | head

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/

sudo journalctl -u kubelet -n 100 --no-pager
ps -ef | grep kubelet
curl -I https://051826735078.dkr.ecr.ap-southeast-1.amazonaws.com
```
