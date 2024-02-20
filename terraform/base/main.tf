locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 3)
}

data "aws_availability_zones" "available" {}


module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "vpc-network"
  cidr = var.vpc_cidr

  azs             = local.availability_zones
  private_subnets = [for k, v in local.availability_zones : cidrsubnet(var.vpc_cidr, 8, k)]
  public_subnets  = [for k, v in local.availability_zones : cidrsubnet(var.vpc_cidr, 8, k + 48)]

  private_subnet_tags = {
    "Tier" = "Private"
  }

  public_subnet_tags = {
    "Tier" = "Public"
  }

  enable_nat_gateway = true
  single_nat_gateway = true
}

# storage buckets for training artifacts
resource "aws_s3_bucket" "training_bucket" {
  bucket        = "${var.account}-training-artifacts"
  force_destroy = true
}

# Container Registry Repositories
resource "aws_ecr_repository" "frontend_ecr" {
  name = "frontend"
}

resource "aws_ecr_repository" "training_ecr" {
  name = "training"
}


# Identity federation
resource "aws_iam_openid_connect_provider" "github_oidc" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = ["a031c46782e6e6c662c2c87c76da9aa62ccabd8e"]
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRoleWithWebIdentity"
    ]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_oidc.arn]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]

    }
  }
}

resource "aws_iam_role" "github_role" {
  name               = "GithubActionsRole"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
}


data "aws_iam_policy_document" "github_policy" {

  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    actions = ["ecr:*"]
    resources = [
      aws_ecr_repository.frontend_ecr.arn,
      aws_ecr_repository.training_ecr.arn
    ]
  }
}

resource "aws_iam_policy" "github_policy" {
  name        = "GithubActionsPolicy"
  description = "Policy for Github Actions"
  policy      = data.aws_iam_policy_document.github_policy.json
}

resource "aws_iam_role_policy_attachment" "github_policy_attachment" {
  policy_arn = aws_iam_policy.github_policy.arn
  role       = aws_iam_role.github_role.name
}

