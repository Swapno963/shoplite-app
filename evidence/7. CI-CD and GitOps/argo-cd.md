## Install ArgoCD in the argocd Namespace
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml




## Verify
kubectl get all -n argocd


## Expose the ArgoCD Server
kubectl port-forward svc/argocd-server -n argocd 8080:443


## Get the ArgoCD Admin Password
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 --decode
