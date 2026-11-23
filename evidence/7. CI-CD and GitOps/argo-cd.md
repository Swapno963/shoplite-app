## Install ArgoCD in the argocd Namespace
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml




## Verify
kubectl get all -n argocd


## Expose the ArgoCD Server
kubectl port-forward svc/argocd-server -n argocd 8080:443


## On another terminal
ssh -i ~/.ssh/id_ed25519 -L 8080:127.0.0.1:8080 ubuntu@13.213.41.145

<!-- set kube config -->
export KUBECONFIG=/home/ubuntu/kubeconfig

## Get the ArgoCD Admin Password
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 --decode
