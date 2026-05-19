variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "hongshing"
}

variable "domain_name" {
  description = "Root domain for the application"
  type        = string
  default     = "hongshing.vela.to"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "database_name" {
  description = "RDS database name"
  type        = string
  default     = "hongshing"
}

variable "database_username" {
  description = "RDS master username"
  type        = string
  default     = "hongshing_admin"
}

variable "database_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "database_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory in MiB"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8001
}

variable "secret_key" {
  description = "Secret key for JWT signing"
  type        = string
  sensitive   = true
}

variable "otp_pepper" {
  description = "Pepper for OTP rate limit hashing"
  type        = string
  sensitive   = true
}

variable "owner_email" {
  description = "Restaurant owner email"
  type        = string
  default     = "owner@hongshing.com"
}
