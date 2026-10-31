variable "region" {
  description = "AWS region for all project resources."
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "AWS CLI profile Terraform uses (deployment identity, local only)."
  type        = string
  default     = "scouting-terraform"
}

variable "data_bucket_name" {
  description = "The project's existing S3 data lake bucket (bronze/silver/gold/ml)."
  type        = string
  default     = "hari-baseball-scouting-001800894194-us-east-2-an"
}
