#!/bin/bash
# HongShing — deploy to the single EC2 box.
# Usage: AWS_PROFILE=bridgeway SSH_KEY=bridgeway-portal bash deploy.sh [--infra] [--app-only]
#   --infra     also run `terraform apply` (REVIEW the plan — a replace wipes the DB)
#   --app-only  skip terraform entirely (just rebuild + redeploy app)
set -e

AWS_PROFILE="${AWS_PROFILE:-bridgeway}"
AWS_REGION="us-east-1"
SSH_KEY="${SSH_KEY:-bridgeway-portal}"
HERE="$(cd "$(dirname "$0")" && pwd)"

cd "$HERE/infra-ec2"
if [ "${1:-}" != "--app-only" ]; then
  terraform init -backend-config="profile=$AWS_PROFILE" -reconfigure
  if [ "${1:-}" = "--infra" ]; then
    echo "!! Review carefully — a 'replace' on aws_instance.backend will WIPE the DB."
    terraform apply
    shift || true
  fi
fi

EC2_IP=$(terraform output -raw ec2_public_ip)
ECR_URL=$(terraform output -raw ecr_repository_url)
INSTANCE_ID=$(terraform output -raw ec2_instance_id 2>/dev/null || true)
FQDN=$(terraform output -raw fqdn)
echo "EC2 IP: $EC2_IP   ECR: $ECR_URL   FQDN: $FQDN"

# Start the (scheduled-off) box if it's stopped.
if [ -n "$INSTANCE_ID" ]; then
  STATE=$(aws ec2 describe-instances --profile "$AWS_PROFILE" --region "$AWS_REGION" \
    --instance-ids "$INSTANCE_ID" --query 'Reservations[].Instances[].State.Name' --output text 2>/dev/null || true)
  if [ "$STATE" != "running" ]; then
    echo "Starting EC2 ($STATE → running)..."
    aws ec2 start-instances --profile "$AWS_PROFILE" --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" >/dev/null
    aws ec2 wait instance-running --profile "$AWS_PROFILE" --region "$AWS_REGION" --instance-ids "$INSTANCE_ID"
    sleep 20
  fi
fi

echo "=== Build + push backend image (arm64) ==="
cd "$HERE"
aws ecr get-login-password --profile "$AWS_PROFILE" --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$ECR_URL"
docker build --platform linux/arm64 -t hongshing-backend:latest ./backend
docker tag hongshing-backend:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

echo "=== Build the 3 SPAs ==="
for app in customer-web admin storefront; do
  ( cd "$HERE/$app" && npm ci && npm run build )
done

echo "=== Ship app files ==="
ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${EC2_IP}" \
  "mkdir -p /opt/hongshing/www/customer /opt/hongshing/www/admin /opt/hongshing/www/store && echo '${ECR_URL}:latest' > /opt/hongshing/.backend_image"
# Render the nginx host (__FQDN__) from the box's fqdn before shipping (template-ready).
sed "s/__FQDN__/$FQDN/g" nginx.prod.conf > /tmp/nginx.rendered.conf
scp -i ~/.ssh/${SSH_KEY}.pem docker-compose.prod.yml backup.sh "ec2-user@${EC2_IP}:/opt/hongshing/"
scp -i ~/.ssh/${SSH_KEY}.pem /tmp/nginx.rendered.conf "ec2-user@${EC2_IP}:/opt/hongshing/nginx.prod.conf"
rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" customer-web/dist/  "ec2-user@${EC2_IP}:/opt/hongshing/www/customer/"
rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" admin/dist/         "ec2-user@${EC2_IP}:/opt/hongshing/www/admin/"
rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" storefront/dist/    "ec2-user@${EC2_IP}:/opt/hongshing/www/store/"

echo "=== Bring up the stack ==="
ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${EC2_IP}" << 'ENDSSH'
set -e
cd /opt/hongshing
IMG=$(cat .backend_image)
# .env must already exist (created once during first-time setup — see DEPLOY-EC2.md).
# Append/refresh only the image ref so we never clobber secrets.
grep -q '^BACKEND_IMAGE=' .env && sed -i "s#^BACKEND_IMAGE=.*#BACKEND_IMAGE=$IMG#" .env || echo "BACKEND_IMAGE=$IMG" >> .env

HOST=${IMG%%/*}
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$HOST"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Nightly backup cron (idempotent).
chmod +x /opt/hongshing/backup.sh
( crontab -l 2>/dev/null | grep -v 'hongshing/backup.sh'; echo "0 2 * * * /opt/hongshing/backup.sh >> /opt/hongshing/backups/backup.log 2>&1" ) | crontab -
echo "Deployed. Containers:"; docker compose -f docker-compose.prod.yml ps
ENDSSH
echo "Done → https://hongshing.bridgewayinnovations.ca"
