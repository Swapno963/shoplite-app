## Install proper terraform version
sudo rm -f /usr/local/bin/terraform


cd /tmp

wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip

unzip terraform_1.6.6_linux_amd64.zip

sudo mv terraform /usr/local/bin/


terraform version




# Create a key pair
ssh-keygen -t ed25519 -C "shoplite"

# Import to aws
aws ec2 import-key-pair \
  --key-name shoplite \
  --public-key-material fileb://~/.ssh/id_ed25519.pub \
  --region ap-southeast-1


# Verify
aws ec2 describe-key-pairs \
  --key-names shoplite \
  --region ap-southeast-1

  

cd terraform
cp terraform.tfvars.example terraform.tfvars   # set admin_cidr
cd bootstrap && terraform init && terraform apply
cd .. && terraform init -backend-config=backend.hcl && terraform apply





some import

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