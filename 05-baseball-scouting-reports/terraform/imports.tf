# Adopt resources that were created by hand in Phase 1, so the whole setup is defined in code.
# Not imported on purpose: the state bucket and the terraform-deployer user (Terraform's own foundation),
# and access keys (importing them would put secrets into state).
import {
  to = aws_s3_bucket.data
  id = var.data_bucket_name
}

import {
  to = aws_s3_bucket_public_access_block.data
  id = var.data_bucket_name
}

import {
  to = aws_iam_user.pipeline
  id = "scouting-pipeline"
}

import {
  to = aws_iam_user_policy.pipeline_bucket
  id = "scouting-pipeline:scouting-bucket-access"
}

import {
  to = aws_budgets_budget.monthly
  id = "001800894194:My Monthly Cost Budget"
}
