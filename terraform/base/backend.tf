/******************************************
  Remote backend configuration
 *****************************************/

# setup of the backend s3 bucket that will keep the remote state

terraform {
  backend "s3" {
    bucket = "590184020311-terraform"
    key    = "terraform_state/base"
    region = "eu-central-1"
  }
}
