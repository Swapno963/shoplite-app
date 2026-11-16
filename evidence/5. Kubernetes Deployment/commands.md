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


## Then:
kubectl create namespace shoplite --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic shoplite-secret -n shoplite \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD"


















## For development
helm install shoplite ./shoplite \
-f values-dev.yaml



## For peoduction:
helm upgrade --install shoplite ./shoplite \
-f values-prod.yaml






namespace.yaml	Creates the Kubernetes namespace
serviceaccount.yaml	Creates service identity for pods
configmap.yaml	Non-sensitive application configuration
secrets.yaml	Sensitive configuration and credentials


web-deployment.yaml	Deploy frontend pods
web-service.yaml	Expose frontend internally
catalog-api-deployment.yaml	Deploy API pods
catalog-api-service.yaml	Expose API internally


catalog-api-pdb.yaml	Prevent API downtime during node maintenance
order-worker-deployment.yaml	Deploy background workers
order-worker-hpa.yaml	Auto-scale workers based on CPU
postgres-statefulset.yaml	Deploy PostgreSQL with persistent storage

postgres-service.yaml	Stable DNS endpoint for PostgreSQL
postgres-seed-job.yaml	Initialize database with products
postgres-networkpolicy.yaml	Restrict PostgreSQL access
redis-deployment.yaml	Deploy Redis

redis-service.yaml	Internal endpoint for Redis
redis-networkpolicy.yaml	Restrict Redis access
ingress.yaml	Route external traffic into the cluster4



Now let's go deep, Act as  a senior dev who is explaing to junior dev, who has aws, tarrform, docker knowledge, ​‌


postgres-service.yaml	Stable DNS endpoint for PostgreSQL
postgres-seed-job.yaml	Initialize database with products
postgres-networkpolicy.yaml	Restrict PostgreSQL access
ingress.yaml	Route external traffic into the cluster4


Files content, how they work tougather, while explaing each add a small  description with it's most importent property,behaviour, commonly miss understood


also draw a Full Flow to explain how those component fit in