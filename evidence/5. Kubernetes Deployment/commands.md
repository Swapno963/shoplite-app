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
ingress.yaml	Route external traffic into the cluster