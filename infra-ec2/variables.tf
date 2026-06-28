variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Per-restaurant identifier (PRD-11 / SCRUM-51). Drives all AWS resource names
# (ECR repo, S3 backup bucket, IAM roles, SG, instance tag, schedules) and the
# on-box app dir (/opt/<slug>). One slug = one isolated restaurant clone.
# Provision a new restaurant with -var="slug=<name>" (+ a matching state key via
# `terraform init -backend-config="key=<slug>/terraform.tfstate"`).
variable "slug" {
  description = "Restaurant slug — names every AWS resource for this clone"
  type        = string
  default     = "hongshing"
}

# vela.to is NOT in this account's Route 53 — only bridgewayinnovations.ca is —
# so HongShing gets a subdomain there. nginx + Let's Encrypt serve TLS on the box.
variable "domain_name" {
  description = "Root hosted zone (must already exist in Route 53)"
  type        = string
  default     = "bridgewayinnovations.ca"
}

# Full hostname the box serves. Empty -> <slug>.demo.<domain_name> (demo default).
# Set to the customer's own domain at cutover (e.g. rewards.hongshing.com).
variable "fqdn" {
  description = "Full host the box serves; empty = <slug>.demo.<domain_name>"
  type        = string
  default     = ""
}

variable "ssh_key_name" {
  description = "EC2 key pair for SSH (reuses the existing bridgeway-portal key by default)"
  type        = string
  default     = "bridgeway-portal"
}

# SSH (port 22) is locked to a specific CIDR, never 0.0.0.0/0. No default, so an
# apply must supply it. Find your IP: curl -s https://checkip.amazonaws.com
# then: -var 'ssh_ingress_cidr=["203.0.113.7/32"]'
variable "ssh_ingress_cidr" {
  description = "CIDR(s) allowed to reach SSH. Set to your IP as a /32."
  type        = list(string)

  validation {
    condition     = !contains(var.ssh_ingress_cidr, "0.0.0.0/0")
    error_message = "ssh_ingress_cidr must not be 0.0.0.0/0 — restrict SSH to a specific IP/CIDR."
  }
}

# --- Business-hours schedule (cost control) ---------------------------------

variable "enable_business_hours_schedule" {
  description = "Start the box at the start hour and stop it at the end hour daily"
  type        = bool
  default     = true
}

variable "schedule_timezone" {
  description = "IANA timezone for the start/stop schedule (DST-aware)"
  type        = string
  default     = "America/Toronto"
}

variable "schedule_start_cron" {
  description = "EventBridge cron to START the instance (begin business hours)"
  type        = string
  default     = "cron(0 9 * * ? *)" # 9:00am ET, every day
}

variable "schedule_stop_cron" {
  description = "EventBridge cron to STOP the instance (end business hours)"
  type        = string
  default     = "cron(0 15 * * ? *)" # 3:00pm ET, every day
}
