# ── Business-hours start/stop (cost control) ──
# Start the box at 9am ET, stop it at 3pm ET. While stopped you pay only for the
# EBS volume (~$1.60/mo) — no compute. The customer signup/OTP/rewards APIs are
# down outside these hours (pilot/cost-pause; widen before real launch).
resource "aws_iam_role" "scheduler" {
  count = var.enable_business_hours_schedule ? 1 : 0
  name  = "hongshing-scheduler-ec2"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  count = var.enable_business_hours_schedule ? 1 : 0
  name  = "ec2-start-stop"
  role  = aws_iam_role.scheduler[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ec2:StartInstances", "ec2:StopInstances"]
      Resource = [aws_instance.backend.arn]
    }]
  })
}

resource "aws_scheduler_schedule" "start" {
  count                        = var.enable_business_hours_schedule ? 1 : 0
  name                         = "hongshing-start"
  description                  = "Start HongShing backend at the start of business hours"
  schedule_expression          = var.schedule_start_cron
  schedule_expression_timezone = var.schedule_timezone
  flexible_time_window { mode = "OFF" }
  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:startInstances"
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ InstanceIds = [aws_instance.backend.id] })
  }
}

resource "aws_scheduler_schedule" "stop" {
  count                        = var.enable_business_hours_schedule ? 1 : 0
  name                         = "hongshing-stop"
  description                  = "Stop HongShing backend at the end of business hours"
  schedule_expression          = var.schedule_stop_cron
  schedule_expression_timezone = var.schedule_timezone
  flexible_time_window { mode = "OFF" }
  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ InstanceIds = [aws_instance.backend.id] })
  }
}
