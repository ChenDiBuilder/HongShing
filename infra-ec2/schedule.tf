# ── Business-hours start/stop (cost control) ──
# The window is profile-driven (PRD-12 S5 / SCRUM-62): provision-restaurant.sh
# translates the profile's hours.open/close into schedule_start_cron/stop_cron with a
# ~1h buffer (defaulting to 9am-3pm ET when hours are unset). While stopped you pay
# only for the EBS volume (~$1.60/mo) — no compute. The customer signup/OTP/rewards
# APIs are down outside these hours (pilot/cost-pause; widen before real launch).
#
# ⚠️ LIVE DRIFT (HongShing demo box): the running schedule is PER-DAY and does not
# match the single start/stop resources below. Real hours (per Google, open daily):
# 11am-11pm Mon-Thu, 11am-midnight Fri, 3pm-midnight Sat, 3pm-11pm Sun. So the live
# setup is 4 EventBridge schedules managed via CLI (start ~30m before open, stop ~15m
# before close, America/Toronto):
#   hongshing-start       cron(30 10 ? * MON,TUE,WED,THU,FRI *)   startInstances  (10:30)
#   hongshing-start-late  cron(30 14 ? * SAT,SUN *)               startInstances  (14:30)  (NOT in TF state)
#   hongshing-stop        cron(45 22 ? * MON,TUE,WED,THU,SUN *)   stopInstances   (22:45)
#   hongshing-stop-late   cron(45 23 ? * FRI,SAT *)               stopInstances   (23:45)  (NOT in TF state)
# A `terraform apply` here would revert start/stop to the single-cron vars and orphan
# the two *-late schedules — re-apply the CLI schedules afterward (see
# profiles/hongshing.yaml `hours:`), or `terraform import` the *-late ones first.
resource "aws_iam_role" "scheduler" {
  count = var.enable_business_hours_schedule ? 1 : 0
  name  = "${var.slug}-scheduler-ec2"
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
  name                         = "${var.slug}-start"
  description                  = "Start ${var.slug} backend at the start of business hours"
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
  name                         = "${var.slug}-stop"
  description                  = "Stop ${var.slug} backend at the end of business hours"
  schedule_expression          = var.schedule_stop_cron
  schedule_expression_timezone = var.schedule_timezone
  flexible_time_window { mode = "OFF" }
  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ InstanceIds = [aws_instance.backend.id] })
  }
}
