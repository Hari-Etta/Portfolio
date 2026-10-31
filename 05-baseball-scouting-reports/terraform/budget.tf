# $1/month cost alarm (Phase 1, imported). Excludes credits and refunds, so it warns about REAL usage
# even while free-plan credits pay for it. Account ID is looked up; the alert email comes from terraform.tfvars.
data "aws_caller_identity" "current" {}

resource "aws_budgets_budget" "monthly" {
  account_id        = data.aws_caller_identity.current.account_id
  billing_view_arn  = "arn:aws:billing::${data.aws_caller_identity.current.account_id}:billingview/primary"
  name              = "My Monthly Cost Budget"
  budget_type       = "COST"
  limit_amount      = "1.0"
  limit_unit        = "USD"
  metrics           = ["UnblendedCost"]
  time_unit         = "MONTHLY"
  time_period_start = "2026-10-01_00:00"
  time_period_end   = "2087-06-15_00:00"
  tags              = {}

  filter_expression {
    not {
      dimensions {
        key           = "RECORD_TYPE"
        match_options = []
        values        = ["Credit", "Refund"]
      }
    }
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 85
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = []
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = []
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
    subscriber_sns_topic_arns  = []
  }
}
