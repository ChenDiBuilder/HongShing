resource "aws_sns_topic" "sms" {
  name = "${var.app_name}-sms-${var.environment}"
}
