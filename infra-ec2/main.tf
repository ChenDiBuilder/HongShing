# HongShing — single-box EC2 deployment (pilot-economics alternative to the
# Fargate stack in ../infra). One t4g.micro runs Postgres + the FastAPI backend
# + nginx (which also serves the three Vite SPAs). No ALB, no RDS, no NAT.
#
# Reuses the portal's existing Terraform state bucket + lock table (already
# created in this account) with a HongShing-scoped key.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }
  backend "s3" {
    bucket         = "bridgeway-terraform-state-274016496814"
    key            = "hongshing/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "bridgeway-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = var.slug
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
