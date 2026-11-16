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