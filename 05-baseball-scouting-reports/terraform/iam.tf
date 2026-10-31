# Pipeline identity: can only read/write/delete objects in the data bucket (least privilege).
# Its access keys are managed by hand, NOT by Terraform (importing keys would put secrets in state).
resource "aws_iam_user" "pipeline" {
  name = "scouting-pipeline"
  path = "/"

  lifecycle {
    # AWS stores access-key descriptions as tags named after key IDs; keep those out of code and plans.
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_user_policy" "pipeline_bucket" {
  name = "scouting-bucket-access"
  user = aws_iam_user.pipeline.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.data.arn}/*"
      }
    ]
  })
}
