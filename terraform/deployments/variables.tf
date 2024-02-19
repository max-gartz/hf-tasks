variable "account" {
  description = "AWS account id"
  type        = string
}

variable "region" {
  description = "Default AWS region for resources"
  type        = string
}

variable "domain" {
  description = "Domain name for Load Balancer"
  type        = string
}

variable "admin_email" {
  description = "Admin email for cognito"
  type        = string
}