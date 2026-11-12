variable "project_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH to the bastion."
  type        = string
}

variable "alb_security_group_id" {
  type = string
}

variable "ingress_node_port" {
  type    = number
  default = 30080
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

variable "key_name" {
  description = "Optional EC2 key pair for SSH via the bastion."
  type        = string
  default     = null
}
