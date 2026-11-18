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
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        "repo:Swapno963/shoplite-app:ref:refs/heads/main"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "github-actions-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role" "terraform_plan" {

  name = "terraform-plan-role"

  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role_policy" "terraform_plan" {

  role = aws_iam_role.terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [

      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]

        Resource = "*"
      }
    ]
  })
}