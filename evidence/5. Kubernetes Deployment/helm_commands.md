<!-- Run helm from basion -->
scp -i ~/.ssh/id_ed25519 \
-r helm \
ubuntu@13.213.44.151:~/

scp -i ~/.ssh/id_ed25519 \
ansible/artifacts/kubeconfig \
ubuntu@13.213.44.151:~/



<!-- Go to the basion -->
ssh -i ~/.ssh/id_ed25519 ubuntu@13.213.44.151



curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
 
chmod +x kubectl
 
sudo mv kubectl /usr/local/bin/

kubectl version --client




## Install HELM
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh


export KUBECONFIG=~/kubeconfig
kubectl get nodes​‌
kubectl get pods -A

## Build the dependency graph:
helm dependency update .

## Lint the umbrella chart:
helm lint .




<!-- Verify -->
kubectl config view --minify


## For local testing:
export POSTGRES_PASSWORD='my-db-password'
export DJANGO_SECRET_KEY='my-django-secret'
export REDIS_PASSWORD='my-redis-secret'


## Then:
kubectl create namespace shoplite

kubectl create secret generic shoplite-secret -n shoplite \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD"




helm upgrade --install shoplite . \
  -f values-prod.yaml \
  --namespace shoplite 


## Ingress (ALB → NodePort 30080 → nginx)

# The AWS ALB forwards to worker NodePort 30080.
# ShopLite Services are ClusterIP, so ingress-nginx must own that port.
# Do not curl 127.0.0.1:30080 on the bastion — NodePort is on the workers.

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values ~/helm/ingress-nginx-values.yaml \
  --wait

kubectl get svc -n ingress-nginx
kubectl get ingress -n shoplite

# From the bastion, hit a worker private IP (not localhost):
# curl -I http://<worker-private-ip>:30080/

# Browser (no custom domain required):
# http://shoplite-alb-192242708.ap-southeast-1.elb.amazonaws.com/



Verify:
kubectl get all -n shoplite

<!-- kubernetes logs  -->
kubectl describe pod catalog-api-6bf48f7d87-8bv2q -n shoplite
kubectl describe pod order-worker-747bcf75dc-4kmlq -n shoplite


<!-- see container log -->
kubectl logs -n shoplite deploy/catalog-api --tail=100
kubectl logs -n shoplite deploy/order-worker --tail=100
kubectl logs -n shoplite deploy/web --tail=50



<!-- 2. Restart deployments -->
kubectl rollout restart deployment catalog-api -n shoplite

kubectl rollout restart deployment web -n shoplite

kubectl rollout restart deployment order-worker -n shoplite



<!-- 3. Watch pods -->
kubectl get pods -n shoplite -w







<!-- Before applying, it's a good practice to see what will change: -->
helm diff upgrade shoplite . \
  -f values-prod.yaml \
  --namespace shoplite


<!-- If you don't have the plugin: -->
helm plugin install https://github.com/databus23/helm-diff




aws sts get-caller-identity
aws ecr get-login-password --region ap-southeast-1 | head

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
-H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

curl -s \
-H "X-aws-ec2-metadata-token: $TOKEN" \
http://169.254.169.254/latest/meta-data/iam/security-credentials/

sudo journalctl -u kubelet -n 100 --no-pager


curl -I https://051826735078.dkr.ecr.ap-southeast-1.amazonaws.com




<!-- Check if kubelet has ECR credential provider configured -->
ps -ef | grep kubelet










Now let's go deep, Act as  a senior dev who is explaing to junior dev, who has aws, tarrform, docker knowledge, ​‌


postgres-service.yaml	Stable DNS endpoint for PostgreSQL
postgres-seed-job.yaml	Initialize database with products
postgres-networkpolicy.yaml	Restrict PostgreSQL access
ingress.yaml	Route external traffic into the cluster4


Files content, how they work tougather, while explaing each add a small  description with it's most importent property,behaviour, commonly miss understood


also draw a Full Flow to explain how those component fit in