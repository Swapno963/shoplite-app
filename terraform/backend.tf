terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }


  backend "s3" {
    bucket         = "shoplite-tfstate-f3b50621"
    key            = "infra/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "shoplite-terraform-locks"
    encrypt        = true
  }
}
