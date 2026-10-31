# Remote state in a dedicated, versioned, private S3 bucket (created once with the AWS CLI).
# use_lockfile = true: Terraform holds a lock file in S3 while running, so two runs can't collide.
terraform {
  backend "s3" {
    bucket       = "hari-scouting-tfstate-001800894194"
    key          = "baseball-scouting/terraform.tfstate"
    region       = "us-east-2"
    profile      = "scouting-terraform"
    encrypt      = true
    use_lockfile = true
  }
}
