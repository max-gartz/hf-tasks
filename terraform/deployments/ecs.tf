locals {
  ecs_name                = "ecs"
  frontend_container_port = 7860
  frontend_container_name = "frontend"
  frontend_service_name   = "${local.ecs_name}-${local.frontend_container_name}"
}

data "aws_iam_policy_document" "frontend_policy" {
  statement {
    actions = ["sagemaker:InvokeEndpoint"]
    resources = [
      "arn:aws:sagemaker:${var.region}:${var.account}:endpoint/${module.huggingface_sagemaker.sagemaker_endpoint_name}"
    ]
  }
}

resource "aws_iam_policy" "frontend_policy" {
  name        = "FrontendTaskPolicy"
  description = "Policy for frontend service task"
  policy      = data.aws_iam_policy_document.frontend_policy.json
}

module "ecs_cluster" {
  source       = "terraform-aws-modules/ecs/aws//modules/cluster"
  version      = "5.9.0"
  cluster_name = local.ecs_name

  task_exec_iam_role_use_name_prefix = false
  task_exec_iam_role_name            = "${var.account}-${local.ecs_name}-task-exec-role"

  cluster_configuration = {
    execute_command_configuration = {
      logging = "OVERRIDE"
      log_configuration = {
        cloud_watch_log_group_name = "/aws/ecs/aws-ec2"
      }
    }
  }

  fargate_capacity_providers = {
    FARGATE = {
      default_capacity_provider_strategy = {
        weight = 100
      }
    }
  }
}

module "ecs_services" {
  source  = "terraform-aws-modules/ecs/aws//modules/service"
  version = "5.9.0"

  name        = local.ecs_name
  cluster_arn = module.ecs_cluster.arn

  cpu    = 256
  memory = 512

  container_definitions = {
    (local.frontend_container_name) = {
      cpu       = 256
      memory    = 512
      essential = true
      image     = "${var.account}.dkr.ecr.${var.region}.amazonaws.com/frontend:latest"
      port_mappings = [
        {
          name          = local.frontend_container_name
          containerPort = local.frontend_container_port
          hostPort      = local.frontend_container_port
          protocol      = "tcp"
        }
      ]
      enable_cloudwatch_logging = true
      readonly_root_filesystem  = false
      memory_reservation        = 100

      environment = [
        {
          name  = "SAGEMAKER_ENDPOINT"
          value = module.huggingface_sagemaker.sagemaker_endpoint_name
        },
        {
          name  = "SAGEMAKER_REGION"
          value = var.region
        }
      ]
    }
  }

  load_balancer = {
    service = {
      target_group_arn = element(module.alb.target_group_arns, 0)
      container_name   = local.frontend_container_name
      container_port   = local.frontend_container_port
    }
  }

  assign_public_ip = false
  subnet_ids       = data.aws_subnets.private_subnets.ids

  task_exec_iam_role_use_name_prefix = false
  task_exec_iam_role_name            = "${var.account}-${local.frontend_service_name}-task-exec-role"
  tasks_iam_role_use_name_prefix     = false
  tasks_iam_role_name                = "${var.account}-${local.frontend_service_name}-task-role"
  tasks_iam_role_policies = {
    "AmazonSageMakerInvokeEndpoint" = aws_iam_policy.frontend_policy.arn,
  }

  create_security_group = false
  security_group_ids    = [aws_security_group.frontend_sg.id]
}

/******************************************
  Security rules
 *****************************************/

resource "aws_security_group" "frontend_sg" {
  name   = "${local.frontend_service_name}-ecs-service-sg"
  vpc_id = data.aws_vpc.vpc.id
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "frontend_ingress_rule" {
  type                     = "ingress"
  security_group_id        = aws_security_group.frontend_sg.id
  protocol                 = "tcp"
  from_port                = local.frontend_container_port
  to_port                  = local.frontend_container_port
  source_security_group_id = module.alb_sg.security_group_id
}

resource "aws_security_group_rule" "frontend_egress_rule" {
  type              = "egress"
  security_group_id = aws_security_group.frontend_sg.id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
}


/******************************************
  Application load balancer
 *****************************************/

module "alb_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 5.0"

  name        = "${local.ecs_name}-service-alb-sg"
  description = "${local.ecs_name} service security group"
  vpc_id      = data.aws_vpc.vpc.id

  ingress_rules = [
    "http-80-tcp",
    "https-443-tcp",
  ]
  ingress_cidr_blocks = ["0.0.0.0/0"]

  egress_rules       = ["all-all"]
  egress_cidr_blocks = ["0.0.0.0/0"]
}

module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 8.0"

  name = "${local.ecs_name}-alb"

  load_balancer_type = "application"

  vpc_id          = data.aws_vpc.vpc.id
  subnets         = data.aws_subnets.public_subnets.ids
  security_groups = [module.alb_sg.security_group_id]

  http_tcp_listeners = [
    {
      port        = 80
      protocol    = "HTTP"
      action_type = "redirect"
      redirect = {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    },
  ]

  https_listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      certificate_arn    = aws_acm_certificate.https_cert.arn
      target_group_index = 0
      action_type        = "authenticate-cognito"
      authenticate_cognito = {
        user_pool_arn       = aws_cognito_user_pool.user_pool.arn
        user_pool_client_id = aws_cognito_user_pool_client.app_client.id
        user_pool_domain    = aws_cognito_user_pool_domain.user_pool_domain.domain
      }
    }
  ]

  target_groups = [
    {
      name             = local.frontend_service_name
      backend_protocol = "HTTP"
      backend_port     = local.frontend_container_port
      target_type      = "ip"
    },
  ]
}

