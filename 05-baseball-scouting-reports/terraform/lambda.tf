# Daily MLB roster + transaction pull: EventBridge Scheduler -> Lambda -> S3 bronze.
# Code package: ../build/lambda.zip (built by build_lambda.ps1). pandas/pyarrow from AWS SDK for pandas layer.
# Least privilege: the function may only write bronze/mlb/* and its own logs; the scheduler may only invoke it.

data "aws_ssm_parameter" "pandas_layer" {
  # Official AWS SDK for pandas layer, pinned to library 3.18.0 for Python 3.13 / x86_64.
  name = "/aws/service/aws-sdk-pandas/3.18.0/py3.13/x86_64/layer-arn"
}

locals {
  lambda_name = "scouting-daily-mlb-pull"
  lambda_zip  = "${path.module}/../build/lambda.zip"
}

resource "aws_cloudwatch_log_group" "daily_pull" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = 14
}

# ---------- Lambda execution role ----------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "daily_pull" {
  name               = "${local.lambda_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "daily_pull" {
  name = "write-mlb-bronze-and-logs"
  role = aws_iam_role.daily_pull.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "WriteMlbBronze"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.data.arn}/bronze/mlb/*"
      },
      {
        Sid      = "WriteOwnLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.daily_pull.arn}:*"
      }
    ]
  })
}

# ---------- Lambda function ----------
resource "aws_lambda_function" "daily_pull" {
  function_name    = local.lambda_name
  role             = aws_iam_role.daily_pull.arn
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  handler          = "src.ingest.daily_handler.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 120
  memory_size      = 512
  layers           = [data.aws_ssm_parameter.pandas_layer.insecure_value]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.daily_pull, aws_iam_role_policy.daily_pull]
}

# ---------- Scheduler: every day at 6:00 AM Denver time ----------
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.lambda_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "invoke-daily-pull-only"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.daily_pull.arn
    }]
  })
}

resource "aws_scheduler_schedule" "daily_pull" {
  name                         = local.lambda_name
  schedule_expression          = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "America/Denver"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.daily_pull.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({})

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}

output "daily_pull_function_name" {
  value = aws_lambda_function.daily_pull.function_name
}
