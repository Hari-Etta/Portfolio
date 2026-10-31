# The project's S3 data lake (bronze / silver / gold / ml). Created in Phase 1, imported into Terraform.
# prevent_destroy: Terraform will refuse any plan that would delete this bucket.
resource "aws_s3_bucket" "data" {
  bucket              = var.data_bucket_name
  bucket_namespace    = "account-regional"
  force_destroy       = false
  object_lock_enabled = false
  tags                = {}

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
