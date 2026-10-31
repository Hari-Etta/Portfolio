terraform {
  required_version = ">= 1.10"   # 1.10+ supports S3 native state locking (use_lockfile)

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.70, < 7.0"
    }
  }
}
