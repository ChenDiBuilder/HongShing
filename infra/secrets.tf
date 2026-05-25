resource "aws_secretsmanager_secret" "app" {
  name        = "${var.app_name}/app/${var.environment}"
  description = "Application secrets"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    secret_key   = var.secret_key
    otp_pepper   = var.otp_pepper
    database_url = "override-via-cli"
    cors_origins = "https://${var.domain_name},https://www.${var.domain_name}"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
