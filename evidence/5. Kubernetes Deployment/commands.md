## Install HELM
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh


## Build the dependency graph:
helm dependency update .

## Lint the umbrella chart:
helm lint .

## Render templates to verify:
helm template mystack . | head -100




## For local testing:
export POSTGRES_PASSWORD='my-db-password'
export DJANGO_SECRET_KEY='my-django-secret'
export REDIS_PASSWORD='my-redis-secret'

To run from host machine
kubectl \
  --kubeconfig=$HOME/.kube/shoplite-config \
  get nodes

or 
mkdir -p ~/.kube

cp admin.conf ~/.kube/config

chmod 600 ~/.kube/config


## Then:
kubectl create namespace shoplite --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic shoplite-secret -n shoplite \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD"





## Check kubeconfig existance in basion 
ls -la ~/.kube/
kubectl get nodes




## Store kubeconfig Locally
mkdir -p ~/.kube

cp kubeconfig.yaml ~/.kube/config

chmod 600 ~/.kube/config




## Verify Cluster Access
kubectl cluster-info


## Render Templates Before Deploying(This shows exactly what Kubernetes will receive.)
helm template shoplite .


## Dry Run(Validate against the cluster):
helm upgrade --install shoplite . \
  --namespace shoplite \
  --dry-run


## For development
helm install shoplite ./shoplite \
-f values-dev.yaml



## For peoduction:
helm upgrade --install shoplite ./shoplite \
-f values-prod.yaml










Now let's go deep, Act as  a senior dev who is explaing to junior dev, who has aws, tarrform, docker knowledge, ​‌


postgres-service.yaml	Stable DNS endpoint for PostgreSQL
postgres-seed-job.yaml	Initialize database with products
postgres-networkpolicy.yaml	Restrict PostgreSQL access
ingress.yaml	Route external traffic into the cluster4


Files content, how they work tougather, while explaing each add a small  description with it's most importent property,behaviour, commonly miss understood


also draw a Full Flow to explain how those component fit in