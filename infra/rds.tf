resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-${var.environment}"
  description = "RDS security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "database" {
  name        = "${var.app_name}/database/${var.environment}"
  description = "RDS master credentials"
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username = var.database_username
    password = random_password.database.result
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.database_name
  })
}

resource "aws_db_instance" "main" {
  identifier     = "${var.app_name}-${var.environment}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.database_instance_class

  db_name  = var.database_name
  username = var.database_username
  password = random_password.database.result

  allocated_storage     = var.database_allocated_storage
  max_allocated_storage = 100
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false
  skip_final_snapshot = var.environment != "production"
  deletion_protection = var.environment == "production"

  backup_retention_period = var.environment == "production" ? 7 : 1
  backup_window           = "06:00-07:00"
  maintenance_window      = "sun:07:00-sun:08:00"

  enabled_cloudwatch_logs_exports = ["postgresql"]
}
