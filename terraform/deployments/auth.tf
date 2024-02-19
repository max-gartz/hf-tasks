locals {
  cognito_user_pool_domain_name = var.account
}

resource "aws_cognito_user_pool" "user_pool" {
  name = "ecs-user-pool"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

# Amazon Cognito hosted domain for your sign-up and sign-in webpages
resource "aws_cognito_user_pool_domain" "user_pool_domain" {
  domain       = local.cognito_user_pool_domain_name
  user_pool_id = aws_cognito_user_pool.user_pool.id
}

resource "aws_cognito_user" "admin_user" {
  user_pool_id = aws_cognito_user_pool.user_pool.id
  username     = "admin"
  attributes = {
    email          = "gartz.maximilian@gmail.com"
    email_verified = false
  }
  temporary_password = "HFInterviewTask1."
}


resource "aws_cognito_user_pool_client" "app_client" {
  name                                 = "cognito-app-client"
  user_pool_id                         = aws_cognito_user_pool.user_pool.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid"]
  callback_urls = [
    "https://${var.domain}/",
    "https://${var.domain}/oauth2/idpresponse",
    "https://${var.domain}.auth.${var.region}.amazoncognito.com/saml2/idpresponse",
    "https://${local.cognito_user_pool_domain_name}.auth.${var.region}.amazoncognito.com/saml2/idpresponse"
  ]
}
