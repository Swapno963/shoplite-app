data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "network" {
  source = "./modules/network"

  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  azs                  = local.azs
  public_subnet_cidrs  = ["10.0.0.0/24", "10.0.1.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
}

module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  ingress_node_port = var.ingress_node_port
  route53_zone_id   = var.route53_zone_id
  domain_name       = var.domain_name
}

module "compute" {
  source = "./modules/compute"

  project_name                = var.project_name
  vpc_id                      = module.network.vpc_id
  vpc_cidr                    = module.network.vpc_cidr
  public_subnet_ids           = module.network.public_subnet_ids
  private_subnet_ids          = module.network.private_subnet_ids
  admin_cidr                  = var.admin_cidr
  alb_security_group_id       = module.alb.alb_security_group_id
  ingress_node_port           = var.ingress_node_port
  bastion_instance_type       = var.bastion_instance_type
  control_plane_instance_type = var.control_plane_instance_type
  worker_instance_type        = var.worker_instance_type
  key_name                    = var.key_name
  worker_count                = var.worker_count
}

resource "aws_lb_target_group_attachment" "workers" {
  count = var.worker_count

  target_group_arn = module.alb.target_group_arn
  target_id        = module.compute.worker_instance_ids[count.index]
  port             = var.ingress_node_port
}

module "ecr" {
  source = "./modules/ecr"

  project_name     = var.project_name
  repository_names = ["web", "catalog-api", "order-worker"]
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "1b511abead59c6ce207077c0bf0e0043b1382612"
  ]
}

data "aws_iam_policy_document" "github_oidc" {
  statement {
    sid    = "GitHubActionsOIDC"
    effect = "Allow"

    actions = [
      "sts:AssumeRoleWithWebIdentity"
    ]

    principals {
      type = "Federated"

      identifiers = [
        aws_iam_openid_connect_provider.github.arn
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com"
      ]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        "repo:Swapno963/shoplite-app:*"
      ]
    }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy_attachment" "ecr_power_user" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

resource "aws_iam_role" "github_actions" {
  name               = "github-actions-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role" "terraform_plan" {
  name               = "terraform-plan-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role_policy_attachment" "terraform_plan_readonly" {
  role       = aws_iam_role.terraform_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

data "aws_iam_policy_document" "terraform_plan_state" {
  statement {
    sid    = "StateBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::shoplite-tfstate-535d4a18"
    ]
  }

  statement {
    sid    = "StateObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::shoplite-tfstate-535d4a18/*"
    ]
  }

  statement {
    sid    = "StateLocks"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
      "dynamodb:DescribeTable"
    ]
    resources = [
      "arn:aws:dynamodb:ap-southeast-1:${data.aws_caller_identity.current.account_id}:table/shoplite-terraform-locks"
    ]
  }
}

resource "aws_iam_role_policy" "terraform_plan" {
  role   = aws_iam_role.terraform_plan.id
  policy = data.aws_iam_policy_document.terraform_plan_state.json
}