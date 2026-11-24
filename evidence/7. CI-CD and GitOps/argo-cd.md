# Argo CD on the cluster

I install Argo CD on the control plane (or any host with kubeconfig), then tunnel the UI through the bastion so I can open it on my laptop.

```bash
export KUBECONFIG=/home/ubuntu/kubeconfig

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl get all -n argocd
```

Wait until `argocd-server` is ready, then:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Leave that running. On your laptop, another terminal:

```bash
ssh -i ~/.ssh/id_ed25519 -L 8080:127.0.0.1:8080 ubuntu@13.213.41.145
```

Use the current bastion IP. UI: https://localhost:8080 (self-signed cert, that's fine).

Admin password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 --decode
echo
```

User is `admin`. After login, add both GitHub repos if they are private, then apply the Applications from **shoplite-gitops**:

```bash
kubectl apply -n argocd -f apps/argocd-applications/
```

That folder has the `shoplite` AppProject plus `shoplite-dev` and `shoplite-prod`. Secrets (`shoplite-secret`) still have to exist in those namespaces. More context is in `shoplite-gitops/README.MD`.
