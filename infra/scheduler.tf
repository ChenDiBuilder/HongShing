# ---------------------------------------------------------------------------
# Business-hours scheduling (cost control)
#
# HongShing is a pilot. The only dedicated, schedulable cost is the single
# Fargate task, so we scale the ECS service to the running count during
# business hours and to 0 outside them. Running 9am–3pm ET (6h/day) instead
# of 24/7 cuts the Fargate line by ~75% (~$18/mo -> ~$4.50/mo).
#
# The static customer/admin SPAs (S3 + CloudFront) stay up regardless — only
# the backend API (signup/OTP/rewards) is down outside business hours.
#
# EventBridge Scheduler calls ecs:UpdateService at the start/stop hours. The
# ECS service ignores desired_count drift (see ecs.tf) so Terraform does not
# fight the scheduler on the next apply.
# ---------------------------------------------------------------------------

# IAM role the scheduler assumes to flip the service's desired count.
resource "aws_iam_role" "scheduler" {
  count = var.enable_business_hours_schedule ? 1 : 0
  name  = "${var.app_name}-scheduler-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "scheduler.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "scheduler_ecs" {
  count = var.enable_business_hours_schedule ? 1 : 0
  name  = "${var.app_name}-scheduler-ecs-${var.environment}"
  role  = aws_iam_role.scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices"]
        Resource = [aws_ecs_service.backend.id]
      }
    ]
  })
}

# Scale UP at the start of business hours -> desired_count = var.ecs_desired_count
resource "aws_scheduler_schedule" "scale_up" {
  count                        = var.enable_business_hours_schedule ? 1 : 0
  name                         = "${var.app_name}-scale-up-${var.environment}"
  schedule_expression          = var.schedule_start_cron
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler[0].arn

    input = jsonencode({
      Cluster      = aws_ecs_cluster.main.name
      Service      = aws_ecs_service.backend.name
      DesiredCount = var.ecs_desired_count
    })
  }
}

# Scale DOWN at the end of business hours -> desired_count = 0
resource "aws_scheduler_schedule" "scale_down" {
  count                        = var.enable_business_hours_schedule ? 1 : 0
  name                         = "${var.app_name}-scale-down-${var.environment}"
  schedule_expression          = var.schedule_stop_cron
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler[0].arn

    input = jsonencode({
      Cluster      = aws_ecs_cluster.main.name
      Service      = aws_ecs_service.backend.name
      DesiredCount = 0
    })
  }
}
