# Terraform — AWS for ShopLite

I pin Terraform to **1.6.6** so the backend and modules behave the same as on my laptop.

```bash
sudo rm -f /usr/local/bin/terraform
cd /tmp
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

## SSH key AWS already knows

```bash
ssh-keygen -t ed25519 -C "shoplite"

aws ec2 import-key-pair \
  --key-name shoplite \
  --public-key-material fileb://~/.ssh/id_ed25519.pub \
  --region ap-southeast-1

aws ec2 describe-key-pairs \
  --key-names shoplite \
  --region ap-southeast-1
```

`terraform.tfvars` should use the same `key_name`.

## Apply

From `shoplite-app`:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# set admin_cidr to your public IP /32

cd bootstrap
terraform init
terraform apply

cd ..
terraform init -backend-config=backend.hcl
terraform apply
```

`bootstrap` is the S3/DynamoDB state backend. The parent module is the VPC, nodes, ALB, ECR, IAM.

After apply, copy `bastion_public_ip`, `vpc_id`, worker private IPs, and ECR URLs. You will need them for Ansible and Helm.

## If IAM already exists in the account

I had to import these once so Terraform would not try to recreate them:

```bash
terraform import \
  aws_iam_openid_connect_provider.github \
  arn:aws:iam::051826735078:oidc-provider/token.actions.githubusercontent.com

terraform import \
  module.compute.aws_iam_role.node \
  shoplite-node-role

terraform import \
  module.compute.aws_iam_role.bastion \
  shoplite-bastion-role

terraform import \
  module.compute.aws_iam_instance_profile.node \
  shoplite-node-profile

terraform import \
  module.compute.aws_iam_instance_profile.bastion \
  shoplite-bastion-profile
```

Skip the imports on a fresh account.
