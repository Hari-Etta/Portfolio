# Terraform uses the dedicated "scouting-terraform" AWS CLI profile (deployment identity, local only).
# Keys live in C:\Users\<you>\.aws\credentials, never in this repo.
provider "aws" {
  region  = var.region
  profile = var.aws_profile
}
