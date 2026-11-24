# ShopLite

Small e-commerce app on a Kubernetes cluster I built on AWS. Customers browse products and place orders; a worker finishes those orders in the background.

This repo is the application, Helm chart, Terraform, Ansible, CI, and observability. Desired state for each environment lives in [shoplite-gitops](https://github.com/Swapno963/shoplite-gitops). Argo CD watches both repos.

## What it does

Someone hits the site through an ALB. Nginx in the cluster routes to **web**. Web talks to **catalog-api**, which writes Postgres and drops a job on Redis. **order-worker** picks that up and updates the order.

Traffic:

```text
User → ALB → ingress-nginx → web → catalog-api
                                    ├── PostgreSQL
                                    └── Redis → order-worker → PostgreSQL
```

## Stack

| Layer | What I used |
|-------|-------------|
| Cloud | AWS (VPC, two AZs, ALB, ECR) |
| Cluster | kubeadm: 1 control plane, 2 workers, private subnets |
| App | web, catalog-api, order-worker |
| Data | PostgreSQL, Redis |
| Ship | GitHub Actions → ECR, Argo CD from Git |
| Watch | Prometheus, Loki, Tempo, Grafana, Alertmanager |

Terraform owns the network, ALB, nodes, and ECR. Ansible hardens and bootstraps the nodes. Helm charts in this repo cover ingress-nginx, the AWS load balancer controller, and observability. ShopLite itself is not `helm upgrade`’d by hand; Argo CD applies `helm/shoplite` plus overlays from gitops.

## Layout

```text
application/     web, catalog-api, order-worker
helm/            shoplite chart and cluster add-ons
terraform/       AWS
ansible/         node setup
.github/         CI, image builds, GitOps tag bumps
evidence/        notes from the build
```

Dev and prod are separate namespaces (`shoplite-dev`, `shoplite-prod`). Image tags for those environments are in gitops `envs/*/values.yaml`.
