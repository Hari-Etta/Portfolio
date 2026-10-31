# Read-only identity for the public Streamlit app. Least privilege: it can READ gold tables and the
# whiff model files only. No writes, no deletes, no access to bronze/silver. Its access key is created
# by hand in Phase 5 (kept out of Terraform state) and stored only in Streamlit secrets.
resource "aws_iam_user" "app_readonly" {
  name = "scouting-app-readonly"
  path = "/"

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_user_policy" "app_readonly" {
  name = "scouting-app-read-gold-and-model"
  user = aws_iam_user.app_readonly.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadGoldAndModel"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = [
          "${aws_s3_bucket.data.arn}/gold/*",
          "${aws_s3_bucket.data.arn}/ml/whiff_model/*"
        ]
      },
      {
        Sid      = "ListOnlyThosePrefixes"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data.arn
        Condition = {
          StringLike = { "s3:prefix" = ["gold/*", "ml/whiff_model/*"] }
        }
      }
    ]
  })
}

output "app_readonly_user_arn" {
  value = aws_iam_user.app_readonly.arn
}
