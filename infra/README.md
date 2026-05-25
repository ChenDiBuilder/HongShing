# HongShing Infrastructure

Terraform-managed AWS infrastructure for the HongShing customer rewards and ordering platform.

## Architecture

```
Route 53 → CloudFront → S3 (customer-web static)
                      → ALB (api.hongshing.vela.to)
                           → ECS Fargate (FastAPI backend)
                                → RDS PostgreSQL 16
                                → SNS (SMS)
                          ECR (Docker images)
                          Secrets Manager
                          CloudWatch Logs
```

## Prerequisites

1. AWS CLI configured with admin credentials
2. Terraform ≥ 1.5
3. Docker (for local image building)
4. A Route 53 hosted zone for your domain (e.g., `hongshing.vela.to`)

## First-Time Setup

### 1. Create Terraform State Backend

Terraform state is stored in S3 with DynamoDB locking. Create these manually first:

```bash
aws s3 mb s3://hongshing-terraform-state --region us-east-1
aws dynamodb create-table \
  --table-name hongshing-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Then uncomment the `backend "s3"` block in `versions.tf`.

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` — generate strong values for `secret_key` and `otp_pepper`:

```bash
openssl rand -hex 32  # for secret_key
openssl rand -hex 16  # for otp_pepper
```

### 3. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan
terraform apply
```

This creates: VPC, RDS, ECS cluster, ALB, S3 buckets, CloudFront, ECR repos, Secrets Manager, SNS topic, IAM roles, Route 53 records, and ACM certificate.

### 4. Build and Push Docker Images

```bash
# Backend
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(terraform output -raw ecr_backend_url)
docker build -t hongshing-backend -f ../backend/Dockerfile ../backend/
docker tag hongshing-backend:latest $(terraform output -raw ecr_backend_url):latest
docker push $(terraform output -raw ecr_backend_url):latest

# Customer web
docker build -t hongshing-customer-web -f ../customer-web/Dockerfile ../customer-web/
# (The customer-web is deployed via S3+CloudFront, Docker image is optional)
```

### 5. Deploy Frontend

```bash
cd ../customer-web
npm ci
npm run build

# Deploy to S3
aws s3 sync dist/ s3://$(cd ../infra && terraform output -raw s3_frontend_bucket)/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $(cd ../infra && terraform output -raw cloudfront_distribution_id) \
  --paths "/*"
```

### 6. Run Database Migrations

The backend auto-creates tables on startup (`create_all`). For production, run Alembic migrations:

```bash
# From the ECS task or a jump host connected to the VPC:
cd backend
DATABASE_URL=$(aws secretsmanager get-secret-value \
  --secret-id hongshing/app/production \
  --query SecretString --output text | jq -r .database_url) \
  alembic upgrade head
```

### 7. Create Initial Admin User

```bash
# Via ECS exec or from within the VPC:
cd backend
python -m app.cli create-owner --email owner@hongshing.com --password <secure-password>
```

## GitHub Actions

Add these secrets to your GitHub repository:

| Secret | Value |
|--------|-------|
| `AWS_ROLE_ARN` | ARN of the GitHub Actions OIDC role |
| `CLOUDFRONT_DISTRIBUTION_ID` | From `terraform output cloudfront_distribution_id` |

## Tearing Down

```bash
# First, manually empty S3 buckets (Terraform won't delete non-empty buckets)
aws s3 rm s3://hongshing-frontend-production --recursive
aws s3 rm s3://hongshing-assets-production --recursive

cd infra
terraform destroy
```

## Cost Estimate (Monthly)

| Service | Approx Cost | Notes |
|---------|------------|-------|
| RDS db.t4g.micro (20GB) | ~$19 | $17 instance + $2 storage |
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 | Single task, always-on |
| Application Load Balancer | ~$22 | One ALB, low traffic |
| CloudFront + S3 | ~$1 | Minimal storage, free tier covers requests |
| Secrets Manager | ~$1 | Two secrets |
| SNS (SMS) | Pay per message | ~$0.01/msg in US |
| **Total** | **~$58/month** | |

### Savings applied

| Removed | Saved | Reason |
|---------|-------|--------|
| NAT Gateway | **-$35/mo** | ECS now in public subnets. RDS stays in private — no outbound internet needed. |
| ALB (future) | **-$22/mo** | Could replace with CloudFront VPC Origin direct to Fargate (requires later CloudFront update). |

### Off-hours savings (not yet implemented)

An EventBridge schedule to stop RDS (11pm-7am) and scale ECS to 0 would save ~$10/month more.
