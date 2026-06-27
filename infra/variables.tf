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

# --- Cost control -----------------------------------------------------------

variable "enable_business_hours_schedule" {
  description = "Scale the backend to 0 outside business hours via EventBridge Scheduler"
  type        = bool
  default     = true
}

variable "schedule_timezone" {
  description = "IANA timezone for the business-hours schedule (DST-aware)"
  type        = string
  default     = "America/Toronto"
}

variable "schedule_start_cron" {
  description = "EventBridge cron to scale the service UP (start of business hours)"
  type        = string
  default     = "cron(0 9 * * ? *)" # 9:00am, every day
}

variable "schedule_stop_cron" {
  description = "EventBridge cron to scale the service DOWN to 0 (end of business hours)"
  type        = string
  default     = "cron(0 15 * * ? *)" # 3:00pm, every day
}

variable "enable_container_insights" {
  description = "Enable ECS Container Insights (extra CloudWatch cost). Off for the pilot."
  type        = bool
  default     = false
}
