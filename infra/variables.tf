variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "hongshing"
}

variable "domain_name" {
  description = "Root domain"
  type        = string
  default     = "hongshing.vela.to"
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
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
