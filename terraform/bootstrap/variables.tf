variable "aws_region" {
  description = "AWS region for the state bucket and lock table."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Name prefix for remote-state resources."
  type        = string
  default     = "shoplite"
}

variable "state_bucket_name" {
  description = "Optional globally unique S3 bucket name. If empty, a random suffix is appended."
  type        = string
  default     = ""
}
