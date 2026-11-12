terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }

  # Apply terraform/bootstrap first, then:
  #   terraform init -backend-config=backend.hcl
  backend "s3" {
    bucket         = "shoplite-terraform-state"
    key            = "infra/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "shoplite-terraform-locks"
    encrypt        = true
  }
}
