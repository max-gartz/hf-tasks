variable "account" {
  description = "AWS account id"
  type        = string
}

variable "region" {
  description = "Default AWS region for resources"
  type        = string
}

variable "vpc_cidr" {
  description = "IP range for VPC"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

