# Access VPC from base configuration
data "aws_vpc" "vpc" {
  id = "vpc-039870a5b8ad7d273"
}

data "aws_subnets" "private_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.vpc.id]
  }
  tags = {
    Tier = "Private"
  }
}

data "aws_subnets" "public_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.vpc.id]
  }
  tags = {
    Tier = "Public"
  }
}


# Wildcard SSL certificate for the domain and all subdomains
resource "aws_acm_certificate" "https_cert" {
  domain_name       = var.domain
  validation_method = "DNS"
}

# Sagemaker endpoint with text classifier
module "huggingface_sagemaker" {
  source               = "./modules/huggingface_sagemaker"
  name_prefix          = "deploy-hub"
  pytorch_version      = "2.1.0"
  transformers_version = "4.37.0"
  instance_type        = "ml.t2.medium"
  hf_model_id          = "max-gartz/distilbert-tweet_eval-emotion"
  hf_task              = "text-classification"
  serverless_config = {
    max_concurrency   = 1
    memory_size_in_mb = 1024
  }
}

