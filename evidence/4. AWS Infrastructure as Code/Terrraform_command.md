cd terraform
cp terraform.tfvars.example terraform.tfvars   # set admin_cidr
cd bootstrap && terraform init && terraform apply
cd .. && terraform init -backend-config=backend.hcl && terraform apply