# ShopLite — set up the platform from scratch

When AWS, the Kubernetes cluster, and the apps are gone and needed to bring everything back.

**ShopLite the application is no longer installed with Helm.** Helm is only for cluster add-ons (ingress-nginx, AWS Load Balancer Controller, observability). The app is deployed by Argo CD from Git.

Related notes:

- Terraform / Ansible: `evidence/4. AWS Infrastructure as Code/`
- Old Helm app install (do not use for ShopLite): `evidence/5. Kubernetes Deployment/helm_commands.md`
- Observability Helm: `evidence/6. Observability/commands.md`
- Argo CD UI tunnel: `evidence/7. CI-CD and GitOps/argo-cd.md`
- GitOps Applications: repo `shoplite-gitops`

```text
You' (laptop/vm)
  → Terraform (AWS VPC, EC2, ALB, ECR, IAM)
  → Ansible (kubeadm, CNI, EBS CSI, ECR image pull)
  → Helm (ingress-nginx, optional monitoring)
  → Argo CD
  → Git repos + shoplite-secret
  → Application CRs (shoplite-dev, shoplite-prod)
  → Argo CD installs Helm chart helm/shoplite from Git
```

Repos:


| Repo                                               | Role                                                                       |
| -------------------------------------------------- | -------------------------------------------------------------------------- |
| `https://github.com/Swapno963/shoplite-app.git`    | App source, Helm chart `helm/shoplite`, GitHub Actions, Terraform, Ansible |
| `https://github.com/Swapno963/shoplite-gitops.git` | Argo CD `AppProject` + Applications + env values (`envs/dev`, `envs/prod`) |


Region: `ap-southeast-1`. Account used in this project: `051826735078`.

---



## 0. Prerequisites (laptop)

- AWS CLI logged in (`aws sts get-caller-identity`)
- Terraform **1.6.x** (this repo expects `>= 1.6.0`)
- Ansible
- SSH key imported into AWS as key pair `shoplite` (or the name in `terraform.tfvars`)

```bash
sudo rm -f /usr/local/bin/terraform
cd /tmp
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version

ssh-keygen -t ed25519 -C "shoplite"
aws ec2 import-key-pair \
  --key-name shoplite \
  --public-key-material fileb://~/.ssh/id_ed25519.pub \
  --region ap-southeast-1
```

GitHub repo secrets on `shoplite-app` (for CI image push + GitOps tag bump):


| Secret         | Purpose                                                                   |
| -------------- | ------------------------------------------------------------------------- |
| `AWS_ROLE_ARN` | Full ARN of `github-actions-role` (OIDC)                                  |
| `GITOPS_TOKEN` | PAT with **write** on `shoplite-gitops` (CI bumps `envs/dev/values.yaml`) |


Optional: `AWS_TF_PLAN_ROLE_ARN`, `TF_VAR_ADMIN_CIDR` for the PR Terraform plan job.

GitHub OIDC `sub` (2026 immutable claims) on the IAM role trust policy must allow **both**:

```json
"StringLike": {
  "token.actions.githubusercontent.com:sub": [
    "repo:Swapno963/shoplite-app:*",
    "repo:Swapno963@100410169/shoplite-app@1454159317:*"
  ]
}
```

Also allow `sts:TagSession` **or** keep `role-skip-session-tagging: true` on the workflows. Audience: `sts.amazonaws.com`.

---



## 1. Terraform — AWS infrastructure

Work from `shoplite-app/terraform`.

```bash
cd /path/to/shoplite-app/terraform
```

`*.tfvars` is gitignored. Create `terraform.tfvars`:

```hcl
aws_region   = "ap-southeast-1"
project_name = "shoplite"
admin_cidr   = "YOUR_PUBLIC_IP/32"   # SSH to bastion; 0.0.0.0/0 is open to the world
key_name     = "shoplite"
ingress_node_port = 30080
```



### 1.1 State bucket (first time only)

```bash
cd bootstrap
terraform init
terraform apply
cd ..
```

Copy the real bucket name into `backend.hcl` / `backend.tf` if bootstrap created a new one. Current project file uses:

```hcl
bucket         = "shoplite-tfstate-535d4a18"
key            = "infra/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "shoplite-terraform-locks"
encrypt        = true
```



### 1.2 Main stack

```bash
terraform init -backend-config=backend.hcl
terraform apply
terraform output
```

Save outputs. You need at least:

- `bastion_public_ip`
- `control_plane_private_ip`
- `worker_private_ips`
- `alb_dns_name`
- `vpc_id`
- `ecr_repository_urls`

If IAM / OIDC already exists in the account, import instead of creating duplicates (see `evidence/4. AWS Infrastructure as Code/Terrraform_command.md`).

### 1.3 Ansible inventory

Edit `ansible/inventory/hosts.ini` with **new** private IPs and bastion public IP:

```ini
[control_plane]
control-plane-1 ansible_host=<control_plane_private_ip>

[workers]
worker-1 ansible_host=<worker_0_private_ip>
worker-2 ansible_host=<worker_1_private_ip>

[k8s_cluster:children]
control_plane
workers

[k8s_cluster:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/id_ed25519
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o ProxyJump=ubuntu@<bastion_public_ip>'
```

Trust the bastion:

```bash
ssh-keyscan -H <bastion_public_ip> >> ~/.ssh/known_hosts
```

---



## 2. Ansible — Kubernetes cluster

From `shoplite-app/ansible` on the laptop (SSH jumps through the bastion):

```bash
cd /path/to/shoplite-app/ansible

sudo apt-get update -y
sudo apt install software-properties-common -y
sudo apt-add-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible
sudo apt-get install -y locales
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8

ansible all -i inventory/hosts.ini -m ping
ansible-playbook -i inventory/hosts.ini site.yml --syntax-check
ansible-playbook -i inventory/hosts.ini site.yml
```

`site.yml` order:

1. Hardening
2. Prepare nodes
3. Container runtime
4. Kubernetes packages
5. Init control plane
6. CNI
7. Join workers
8. Verify
9. EBS CSI (`gp3` StorageClass)
10. ECR credential provider (kubelet can pull `*.dkr.ecr.*.amazonaws.com`)

Kubeconfig is written under `ansible/artifacts/kubeconfig`. Copy it to the bastion:

```bash
scp -i ~/.ssh/id_ed25519 \
  ansible/artifacts/kubeconfig \
  ubuntu@<bastion_public_ip>:~/kubeconfig
```

---



## 3. Bastion tools

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<bastion_public_ip>

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

export KUBECONFIG=/home/ubuntu/kubeconfig
kubectl get nodes
kubectl get pods -A
```

Copy Helm charts (ingress, observability, LBC values) — **not** as a ShopLite install:

```bash
# from laptop/vm
scp -i ~/.ssh/id_ed25519 -r helm monitoring \
  ubuntu@<bastion_public_ip>:~/
```

---



## 4. Platform Helm (not the ShopLite app)



### 4.1 ingress-nginx (required for ShopLite HTTP)

ALB forwards to worker **NodePort 30080**. ShopLite Services are ClusterIP; nginx must own that port.

The values file lives in this repo (`helm/ingress-nginx-values.yaml`). It must be on the bastion first (`ls ~/helm/ingress-nginx-values.yaml`). If that path is missing, run the `scp` in **§3** from the **laptop** (a new terminal, not inside `ssh`):

```bash
# from laptop, repo root
scp -i ~/.ssh/id_ed25519 -r helm monitoring \
  ubuntu@<bastion_public_ip>:~/
```

Then on the bastion:

```bash
export KUBECONFIG=/home/ubuntu/kubeconfig

ls ~/helm/ingress-nginx-values.yaml

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values ~/helm/ingress-nginx-values.yaml \
  --wait

kubectl get svc -n ingress-nginx
```

`helm/ingress-nginx-values.yaml` sets HTTP NodePort `30080`.

Smoke from the bastion (worker private IP, not localhost):

```bash
curl -I http://<worker_private_ip>:30080/
```

Browser (no custom domain required):

```text
http://<alb_dns_name>
```

Host-based routes (`dev.shoplite.local`) need `/etc/hosts` or DNS pointing at the ALB.

### 4.2 AWS Load Balancer Controller (needed for Grafana Ingress / extra ALBs)

```bash
# VPC_ID from terraform output
export VPC_ID='vpc-xxxxxxxx'

helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --values /home/ubuntu/helm/aws-load-balancer-controller/values.yaml \
  --set vpcId="$VPC_ID" \
  --wait --timeout 5m

kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```



### 4.3 Observability (optional but used in this project)

Full commands: `evidence/6. Observability/commands.md`.

Copy gitignored Slack values to the bastion, then:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cd /home/ubuntu/helm/observability
helm dependency update
helm upgrade --install observability . \
  --namespace monitoring \
  --create-namespace \
  -f /home/ubuntu/helm/observability/values.yaml \
  -f /home/ubuntu/helm/observability/values-slack.yaml \
  --wait --timeout 20m

kubectl get ingress -n monitoring grafana \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
```

ShopLite ServiceMonitors are part of `helm/shoplite`. After Argo CD syncs the app, they appear in `shoplite-dev` / `shoplite-prod` if Prometheus CRDs exist. **Do not** `helm upgrade shoplite` to get ServiceMonitors.

---



## 5. Container images in ECR

Argo CD only deploys **image tags already listed** in `shoplite-gitops` (`envs/dev/values.yaml`, `envs/prod/values.yaml`). Empty ECR → `ImagePullBackOff`.

Build workflows (`.github/workflows/web.yml`, `catalog-api.yml`, `order-worker.yml`) push `${{ github.sha }}` and `stable`, then bump **dev** tags in gitops.

After the cluster exists, push app code on the branch those workflows watch (currently `gitOps`) so images exist. Confirm:

```bash
aws ecr describe-images --repository-name shoplite-web --region ap-southeast-1
aws ecr describe-images --repository-name shoplite-catalog-api --region ap-southeast-1
aws ecr describe-images --repository-name shoplite-order-worker --region ap-southeast-1
```

Set `envs/dev/values.yaml` / `envs/prod/values.yaml` tags to images that exist (`stable` or a commit SHA).

Nodes pull via the Ansible ECR credential provider (`configure-ecr.yml`). If pulls fail:

```bash
ps -ef | grep kubelet
sudo journalctl -u kubelet -n 100 --no-pager
```

---



## 6. Argo CD



### 6.1 Install

```bash
export KUBECONFIG=/home/ubuntu/kubeconfig

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server
kubectl get pods -n argocd
```

`argocd-server` and `argocd-application-controller` must be Running.

Known issue: `applicationsets.argoproj.io` CRD annotations can exceed 262144 bytes. ApplicationSet then stays `Error`. ShopLite uses plain `Application` objects — you can ignore ApplicationSet.

Re-applying install when the namespace already exists is fine (`AlreadyExists` / `unchanged`).

### 6.2 UI from your laptop

Port-forward **on the bastion** only binds the bastion’s localhost. From the **laptop**:

```bash
ssh -i ~/.ssh/id_ed25519 -L 8080:127.0.0.1:8080 ubuntu@<bastion_public_ip>
```

On the bastion:

```bash
export KUBECONFIG=/home/ubuntu/kubeconfig
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Laptop browser: **[https://localhost:8080](https://localhost:8080)** (HTTPS, accept the self-signed cert). `http://` will fail.

Password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
echo
```

User: `admin`.

The `argocd` CLI is **not** installed by the cluster manifests. Prefer the UI or `kubectl` secrets below. Optional CLI:

```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd /usr/local/bin/argocd
```



### 6.3 Register Git repositories (required if private)

Do **not** use `helm upgrade --install shoplite`. Clone gitops and register both GitHub repos.

```bash
export GITOPS_TOKEN='YOUR_PAT'   # contents:read on both repos; never commit this

kubectl -n argocd create secret generic repo-shoplite-app \
  --from-literal=type=git \
  --from-literal=url=https://github.com/Swapno963/shoplite-app.git \
  --from-literal=username=git \
  --from-literal=password="$GITOPS_TOKEN"
kubectl -n argocd label secret repo-shoplite-app argocd.argoproj.io/secret-type=repository

kubectl -n argocd create secret generic repo-shoplite-gitops \
  --from-literal=type=git \
  --from-literal=url=https://github.com/Swapno963/shoplite-gitops.git \
  --from-literal=username=git \
  --from-literal=password="$GITOPS_TOKEN"
kubectl -n argocd label secret repo-shoplite-gitops argocd.argoproj.io/secret-type=repository
```

Or UI: **Settings → Repositories → Connect Repo** (HTTPS, username `git`, password = PAT).

### 6.4 Application secrets (Helm does not create these)

Postgres stores the password **inside the PVC on first start**. Pick a password and do not change it later, or catalog-api will CrashLoop (`password authentication failed`).

```bash
kubectl create namespace shoplite-dev --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace shoplite-prod --dry-run=client -o yaml | kubectl apply -f -

kubectl -n shoplite-dev create secret generic shoplite-secret \
  --from-literal=POSTGRES_PASSWORD='my-db-password' \
  --from-literal=DJANGO_SECRET_KEY='my-django-secret' \
  --from-literal=REDIS_PASSWORD='my-redis-secret'

kubectl -n shoplite-prod create secret generic shoplite-secret \
  --from-literal=POSTGRES_PASSWORD='my-db-password' \
  --from-literal=DJANGO_SECRET_KEY='my-django-secret' \
  --from-literal=REDIS_PASSWORD='my-redis-secret'
```

If you already started Postgres with a different password, delete the **dev** PVC and let Argo recreate Postgres (data loss):

```bash
kubectl -n shoplite-dev delete statefulset postgres --cascade=orphan
kubectl -n shoplite-dev delete pvc --selector=app=postgres
kubectl -n shoplite-dev delete pod postgres-0 --force --grace-period=0
```

Do not wipe `shoplite` / `shoplite-prod` PVCs unless you intend to.

### 6.5 Apply Project + Applications

On the bastion:

```bash
git clone https://github.com/Swapno963/shoplite-gitops.git
cd shoplite-gitops

kubectl apply -n argocd -f apps/argocd-applications/shoplite-project.yaml
kubectl apply -n argocd -f apps/argocd-applications/shoplite-dev.yaml
kubectl apply -n argocd -f apps/argocd-applications/shoplite-prod.yaml
```

Installing Argo CD does **not** create Applications. Until this step the UI shows “No applications available”.


| Resource    | Name            | Sync                                                                        |
| ----------- | --------------- | --------------------------------------------------------------------------- |
| AppProject  | `shoplite`      | Allows the two GitHub repos and namespaces `shoplite-dev` / `shoplite-prod` |
| Application | `shoplite-dev`  | Automated, prune, self-heal                                                 |
| Application | `shoplite-prod` | Automated, self-heal, **no prune**                                          |


Both Applications watch `main` on both repos (`helm/shoplite` + `envs/*/values.yaml`). Chart changes only apply after they are on `shoplite-app` `main`.

```bash
kubectl -n argocd get appproject
kubectl -n argocd get applications
kubectl -n argocd get application shoplite-dev -o yaml | less
```

Wait until `Synced` / `Healthy`. Dev auto-syncs; you do not run `argocd app sync shoplite-dev`.

### 6.6 Namespaces


| Namespace       | What it is                                                                                                                             |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `argocd`        | Argo CD itself                                                                                                                         |
| `shoplite-dev`  | GitOps development                                                                                                                     |
| `shoplite-prod` | GitOps production                                                                                                                      |
| `shoplite`      | **Old** `helm upgrade --install shoplite` install. Not Argo. `kubectl get all -n shoplite` is the wrong place to debug GitOps crashes. |
| `ingress-nginx` | Ingress controller                                                                                                                     |
| `monitoring`    | Optional observability                                                                                                                 |


Debug GitOps catalog-api:

```bash
kubectl get pods -n shoplite-dev
kubectl -n shoplite-dev logs -l app=catalog-api --previous --tail=80
```

---



## 7. Verify the app

```bash
kubectl get pods -n shoplite-dev
kubectl get ingress -n shoplite-dev
kubectl get pods -n shoplite-prod
```

Expect in each env: `web`, `catalog-api`, `order-worker`, `postgres`, `redis` Running.

ALB:

```text
http://<alb_dns_name>
```

Dev host from values: `dev.shoplite.local` (add `/etc/hosts` → ALB if you use that host).

---



## 8. Day-2 (no Helm for the app)

1. Change code in `shoplite-app`, push the branch GitHub Actions watches.
2. CI builds, pushes ECR (`sha` + `stable`), commits a new tag to `shoplite-gitops` `envs/dev/values.yaml`.
3. Argo CD sees Git on `main` and auto-syncs `shoplite-dev`.
4. Production: edit `envs/prod/values.yaml` and push; `shoplite-prod` auto-syncs (no prune).

Do **not** run `helm upgrade shoplite`, `kubectl apply` on app manifests, or `argocd app sync shoplite-dev` for a normal deploy.

Self-heal check (dev):

```bash
kubectl -n shoplite-dev scale deploy web --replicas=5
# wait; replicas return to Git (1)
```

---



## 9. Checklist

- [ ] Terraform applied; inventory IPs match outputs
- [ ] Ansible `site.yml` succeeded; `kubectl get nodes` Ready
- [ ] ECR credential provider on workers
- [ ] ingress-nginx NodePort 30080
- [ ] Images exist in ECR for tags in gitops values
- [ ] Argo CD server Running
- [ ] Both Git repos registered
- [ ] `shoplite-secret` in `shoplite-dev` and `shoplite-prod` (password will not change)
- [ ] Applications applied; `shoplite-dev` Synced/Healthy
- [ ] GitHub `AWS_ROLE_ARN` / `GITOPS_TOKEN` / OIDC `sub` with immutable IDs

---



## 10. What not to do

- Do not `helm upgrade --install shoplite` for a GitOps rebuild (creates a third copy in `shoplite`).
- Do not port-forward Argo CD on the bastion and open `http://localhost:8080` on the laptop without SSH `-L`.
- Do not debug `shoplite-dev` CrashLoop by `kubectl get all -n shoplite`.
- Do not change `POSTGRES_PASSWORD` after Postgres has initialized the PVC.
- Do not commit PATs, `terraform.tfvars`, or kubeconfig.

