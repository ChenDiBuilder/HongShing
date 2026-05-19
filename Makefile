# HongShing — unified deploy Makefile
# Usage: make help

ENV         ?= production
AWS_REGION  ?= us-east-1
APP_NAME    = hongshing
TF_DIR      = infra

# State backend resources (created by make setup-state)
TF_STATE_BUCKET = $(APP_NAME)-terraform-state
TF_LOCK_TABLE   = $(APP_NAME)-terraform-locks

# Phonies
.PHONY: check setup-state init plan apply infra build build-backend build-frontend \
        push-backend deploy-frontend deploy \
        migrate create-admin seed-menu all outputs destroy help

.DEFAULT_GOAL := help

##@ Prerequisites
##   make check

check: ## Verify all required tools are installed
	@printf "\033[0;32m=== Checking prerequisites ===\033[0m\n"
	@command -v aws        >/dev/null 2>&1 || { printf "\033[0;31m✗ aws CLI not found — brew install awscli\033[0m\n"; exit 1; }
	@printf "  ✓ aws CLI\n"
	@command -v terraform  >/dev/null 2>&1 || { printf "\033[0;31m✗ terraform not found — brew install terraform\033[0m\n"; exit 1; }
	@printf "  ✓ terraform\n"
	@command -v docker     >/dev/null 2>&1 || { printf "\033[0;31m✗ docker not found\033[0m\n"; exit 1; }
	@printf "  ✓ docker\n"
	@command -v node       >/dev/null 2>&1 || { printf "\033[0;31m✗ node not found\033[0m\n"; exit 1; }
	@printf "  ✓ node\n"
	@command -v npm        >/dev/null 2>&1 || { printf "\033[0;31m✗ npm not found\033[0m\n"; exit 1; }
	@printf "  ✓ npm\n"
	@command -v python3    >/dev/null 2>&1 || { printf "\033[0;31m✗ python3 not found\033[0m\n"; exit 1; }
	@printf "  ✓ python3\n"
	@printf "\033[0;32mAll prerequisites met.\033[0m\n"

##@ State Backend (one-time)
##   make setup-state

setup-state: check ## Create S3 bucket + DynamoDB for Terraform remote state
	@printf "\033[0;32m=== Setting up Terraform state backend ===\033[0m\n"
	@if aws s3api head-bucket --bucket $(TF_STATE_BUCKET) 2>/dev/null; then \
		printf "  ✓ S3 bucket already exists\n"; \
	else \
		aws s3 mb s3://$(TF_STATE_BUCKET) --region $(AWS_REGION); \
		aws s3api put-bucket-versioning --bucket $(TF_STATE_BUCKET) \
			--versioning-configuration Status=Enabled; \
		aws s3api put-bucket-encryption --bucket $(TF_STATE_BUCKET) \
			--server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'; \
		printf "  ✓ S3 bucket created\n"; \
	fi
	@if aws dynamodb describe-table --table-name $(TF_LOCK_TABLE) --region $(AWS_REGION) 2>/dev/null; then \
		printf "  ✓ DynamoDB table already exists\n"; \
	else \
		aws dynamodb create-table \
			--table-name $(TF_LOCK_TABLE) \
			--attribute-definitions AttributeName=LockID,AttributeType=S \
			--key-schema AttributeName=LockID,KeyType=HASH \
			--billing-mode PAY_PER_REQUEST \
			--region $(AWS_REGION) > /dev/null; \
		printf "  ✓ DynamoDB table created\n"; \
	fi
	@printf "\033[0;32mState backend ready.\033[0m\n"

##@ Infrastructure
##   make infra

init: setup-state ## Initialize Terraform (downloads providers)
	@cd $(TF_DIR) && terraform init

plan: init ## Show what Terraform will create/change
	@cd $(TF_DIR) && terraform plan

apply: init ## Apply Terraform changes (interactive approval)
	@cd $(TF_DIR) && terraform apply

infra: setup-state init ## Full infrastructure deploy (auto-approve)
	@printf "\033[0;32m=== Deploying infrastructure ===\033[0m\n"
	@cd $(TF_DIR) && terraform apply -auto-approve
	@printf "  ✓ VPC, RDS, ECS, ALB, S3, CloudFront, SNS created\n"
	@printf "\033[0;32mInfrastructure deployed.\033[0m\n"
	@printf "  Demo URL: $$(cd $(TF_DIR) && terraform output -raw demo_url)\n"
	@printf "  Next: make build  →  make deploy\n"

##@ Build
##   make build

build-backend: ## Build backend Docker image (tagged as hongshing-backend:latest)
	@printf "\033[0;32m=== Building backend ===\033[0m\n"
	@docker build -t $(APP_NAME)-backend -f backend/Dockerfile backend/
	@printf "  ✓ $(APP_NAME)-backend:latest built\n"

build-frontend: ## Build customer-web SPA into customer-web/dist/
	@printf "\033[0;32m=== Building frontend ===\033[0m\n"
	@cd customer-web && npm ci --silent && npm run build
	@printf "  ✓ customer-web/dist/ ready\n"

build: build-backend build-frontend ## Build both backend and frontend

##@ Deploy
##   make deploy

push-backend: build-backend ## Push Docker image to ECR + redeploy ECS service
	@printf "\033[0;32m=== Deploying backend ===\033[0m\n"
	@ECR_URL=$$(cd $(TF_DIR) && terraform output -raw ecr_backend_url 2>/dev/null); \
	CLUSTER=$$(cd $(TF_DIR) && terraform output -raw ecs_cluster_name 2>/dev/null); \
	SERVICE=$$(cd $(TF_DIR) && terraform output -raw ecs_service_name 2>/dev/null); \
	if [ -z "$$ECR_URL" ]; then \
		printf "\033[0;31m✗ No ECR URL — run 'make infra' first\033[0m\n"; exit 1; fi; \
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $$ECR_URL 2>/dev/null; \
	docker tag $(APP_NAME)-backend:latest $$ECR_URL:latest; \
	docker push $$ECR_URL:latest; \
	printf "  ✓ Image pushed to $$ECR_URL\n"; \
	aws ecs update-service --cluster $$CLUSTER --service $$SERVICE --force-new-deployment >/dev/null; \
	printf "  ✓ ECS service $$SERVICE redeploying\n"

deploy-frontend: build-frontend ## Deploy SPA to S3 + invalidate CloudFront
	@printf "\033[0;32m=== Deploying frontend ===\033[0m\n"
	@BUCKET=$$(cd $(TF_DIR) && terraform output -raw s3_frontend_bucket 2>/dev/null); \
	DIST=$$(cd $(TF_DIR) && terraform output -raw cloudfront_distribution_id 2>/dev/null); \
	if [ -z "$$BUCKET" ]; then \
		printf "\033[0;31m✗ No S3 bucket — run 'make infra' first\033[0m\n"; exit 1; fi; \
	aws s3 sync customer-web/dist/ s3://$$BUCKET/product-demo/hongshing/ --delete --quiet; \
	printf "  ✓ Synced to s3://$$BUCKET/product-demo/hongshing/\n"; \
	if [ -n "$$DIST" ]; then \
		aws cloudfront create-invalidation --distribution-id $$DIST --paths "/product-demo/hongshing/*" >/dev/null; \
		printf "  ✓ CloudFront cache invalidated\n"; fi

deploy: push-backend deploy-frontend ## Deploy backend + frontend to AWS

##@ Database
##   make migrate  (after infra + build + deploy)

migrate: ## Run Alembic database migrations (needs DB access from within VPC)
	@printf "\033[0;32m=== Running migrations ===\033[0m\n"
	@DB_URL=$$(aws secretsmanager get-secret-value \
		--secret-id $(APP_NAME)/app/$(ENV) \
		--query SecretString --output text 2>/dev/null | \
		python3 -c "import sys,json; print(json.load(sys.stdin).get('database_url',''))" 2>/dev/null); \
	if [ -n "$$DB_URL" ]; then \
		cd backend && DATABASE_URL="$$DB_URL" .venv/bin/alembic upgrade head; \
		printf "  ✓ Migrations applied\n"; \
	else \
		printf "\033[0;31m✗ Cannot access database — is the VPC reachable?\033[0m\n"; \
		printf "  Run from within VPC or use 'aws ecs execute-command'\n"; \
	fi

create-admin: ## Create initial admin user (needs DB access)
	@printf "\033[0;32m=== Creating admin user ===\033[0m\n"
	@cd backend && .venv/bin/python -m app.cli create-owner \
		--email $${OWNER_EMAIL:-owner@hongshing.com} \
		--password $${ADMIN_PASSWORD}

seed-menu: ## Seed menu data into RDS (needs DB access)
	@printf "\033[0;32m=== Seeding menu ===\033[0m\n"
	@cd backend && .venv/bin/python -m app.cli seed-menu

##@ Full Pipeline
##   make all

all: setup-state infra build deploy ## Everything — setup → infra → build → deploy
	@printf "\n\033[0;32m╔══════════════════════════════════════════════════════╗\033[0m\n"
	@printf "\033[0;32m║  Deploy complete!                                    ║\033[0m\n"
	@printf "\033[0;32m║  $$(cd $(TF_DIR) && terraform output -raw demo_url)  ║\033[0m\n"
	@printf "\033[0;32m╚══════════════════════════════════════════════════════╝\033[0m\n"

##@ Utilities
##   make outputs

outputs: ## Show all Terraform outputs
	@cd $(TF_DIR) && terraform output

destroy: ## DESTROY all infrastructure (interactive confirmation)
	@printf "\033[0;31m╔══════════════════════════════════════════════╗\033[0m\n"
	@printf "\033[0;31m║  WARNING: Destroys everything — data, DNS.  ║\033[0m\n"
	@printf "\033[0;31m╚══════════════════════════════════════════════╝\033[0m\n"
	@read -p "Type 'destroy' to confirm: " c && [ "$$c" = "destroy" ] || exit 1
	@cd $(TF_DIR) && terraform destroy

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "; printf "\n\033[0;36mUsage:\033[0m\n  make \033[0;33m<target>\033[0m\n"}; \
		{printf "  \033[0;33m%-22s\033[0m %s\n", $$1, $$2}'
	@printf "\n\033[0;36mFlow:\033[0m\n"
	@printf "  \033[0;33mmake all\033[0m            One command to rule them all\n"
	@printf "  \033[0;33mmake check\033[0m          Verify prerequisites\n"
	@printf "  \033[0;33mmake setup-state\033[0m    Create remote state backend\n"
	@printf "  \033[0;33mmake infra\033[0m          Deploy all AWS resources\n"
	@printf "  \033[0;33mmake build\033[0m          Build Docker image + frontend\n"
	@printf "  \033[0;33mmake deploy\033[0m         Push image + redeploy ECS + sync S3\n"
	@printf "  \033[0;33mmake migrate\033[0m        Run DB migrations\n"
	@printf "  \033[0;33mmake seed-menu\033[0m      Populate menu data\n"
	@printf "  \033[0;33mmake create-admin\033[0m   Create initial admin\n\n"
