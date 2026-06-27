resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.app_name}-backend-${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.app_name}-backend-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = "${aws_ecr_repository.backend.repository_url}:latest"
      portMappings = [
        { containerPort = var.container_port, protocol = "tcp" }
      ]
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "S3_BUCKET", value = aws_s3_bucket.assets.id },
        { name = "SNS_SENDER_ID", value = "HongShing" },
        { name = "SNS_ORIGINATION_NUMBER", value = "+12368645995" },
        { name = "OWNER_EMAIL", value = var.owner_email },
      ]
      secrets = [
        { name = "SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:secret_key::" },
        { name = "OTP_PEPPER", valueFrom = "${aws_secretsmanager_secret.app.arn}:otp_pepper::" },
        { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.app.arn}:database_url::" },
        { name = "CORS_ORIGINS", valueFrom = "${aws_secretsmanager_secret.app.arn}:cors_origins::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "backend"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/api/health || exit 1"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])
}

# Target group on Vela's ALB
resource "aws_lb_target_group" "backend" {
  name        = "${var.app_name}-backend-${var.environment}"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.vela.id
  target_type = "ip"

  health_check {
    path                = "/api/health"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  deregistration_delay = 30
}

# Add HK API routing to Vela's ALB
resource "aws_lb_listener_rule" "hongshing_api" {
  listener_arn = data.aws_lb_listener.vela_http.arn
  priority     = 11

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  condition {
    host_header {
      values = [aws_cloudfront_distribution.main.domain_name]
    }
  }
}

resource "aws_ecs_service" "backend" {
  name                   = "${var.app_name}-backend-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.backend.arn
  desired_count          = var.ecs_desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = data.aws_subnets.vela_public.ids
    security_groups  = [data.aws_security_group.vela_ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.container_port
  }

  force_new_deployment               = true
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # The business-hours scheduler (scheduler.tf) owns desired_count at runtime.
  # Ignore drift so `terraform apply` doesn't scale the service back up when it
  # runs while the service is intentionally scaled to 0 outside business hours.
  lifecycle {
    ignore_changes = [desired_count]
  }
}
