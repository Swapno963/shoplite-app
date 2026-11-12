variable "aws_region" {
  description = "AWS region for ShopLite infrastructure."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  type    = string
  default = "shoplite"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH to the bastion host (for example your public IP /32)."
  type        = string
}

variable "ingress_node_port" {
  description = "Kubernetes NodePort that the ALB forwards to."
  type        = number
  default     = 30080
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH via the bastion."
  type        = string
  default     = null
}

variable "route53_zone_id" {
  description = "Optional Route 53 hosted zone ID. Leave empty to skip DNS."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Optional DNS name for the ALB alias record."
  type        = string
  default     = ""
}

variable "bastion_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "control_plane_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "worker_instance_type" {
  type    = string
  default = "t3.medium"
}
