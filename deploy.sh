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
# `slug` output post-dates the live hongshing box's persisted state; fall back to
# the var default so a redeploy never aborts here until the next infra apply.
SLUG=$(terraform output -raw slug 2>/dev/null || echo hongshing)
APP_DIR="/opt/$SLUG"   # box's user_data created /opt/<slug>
# Storefront opt-in (PRD-12 S6 / SCRUM-63). provision-restaurant.sh exports this
# from the profile's storefront.enabled; a standalone deploy defaults to "true"
# so the live box's behaviour is unchanged. When "false", the storefront SPA is
# not built/shipped and no www/store dir is created, so nginx /store/ 404s.
STOREFRONT_ENABLED="${STOREFRONT_ENABLED:-true}"
echo "EC2 IP: $EC2_IP   ECR: $ECR_URL   FQDN: $FQDN   SLUG: $SLUG   APP_DIR: $APP_DIR   storefront: $STOREFRONT_ENABLED"

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
docker build --platform linux/arm64 -t "${SLUG}-backend:latest" ./backend
docker tag "${SLUG}-backend:latest" "$ECR_URL:latest"
docker push "$ECR_URL:latest"

echo "=== Build the SPAs ==="
SPAS=(customer-web admin)
if [ "$STOREFRONT_ENABLED" = "true" ]; then
  SPAS+=(storefront)
else
  echo "  storefront disabled (storefront.enabled=false) — skipping build + ship"
fi
for app in "${SPAS[@]}"; do
  ( cd "$HERE/$app" && npm ci && npm run build )
done

echo "=== Ship app files ==="
# Only create www/store when the storefront is enabled (absent dir => nginx /store/ 404s).
STORE_DIR=""
[ "$STOREFRONT_ENABLED" = "true" ] && STORE_DIR="$APP_DIR/www/store"
ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${EC2_IP}" \
  "mkdir -p $APP_DIR/www/customer $APP_DIR/www/admin $STORE_DIR && echo '${ECR_URL}:latest' > $APP_DIR/.backend_image"
# Render the nginx host (__FQDN__) from the box's fqdn before shipping (template-ready).
sed "s/__FQDN__/$FQDN/g" nginx.prod.conf > /tmp/nginx.rendered.conf
scp -i ~/.ssh/${SSH_KEY}.pem docker-compose.prod.yml backup.sh "ec2-user@${EC2_IP}:$APP_DIR/"
scp -i ~/.ssh/${SSH_KEY}.pem /tmp/nginx.rendered.conf "ec2-user@${EC2_IP}:$APP_DIR/nginx.prod.conf"
rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" customer-web/dist/  "ec2-user@${EC2_IP}:$APP_DIR/www/customer/"
rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" admin/dist/         "ec2-user@${EC2_IP}:$APP_DIR/www/admin/"
if [ "$STOREFRONT_ENABLED" = "true" ]; then
  rsync -az -e "ssh -i ~/.ssh/${SSH_KEY}.pem" storefront/dist/  "ec2-user@${EC2_IP}:$APP_DIR/www/store/"
fi

echo "=== Bring up the stack ==="
# The remote heredoc is single-quoted (no local expansion) — pass APP_DIR through
# the remote shell's environment so $APP_DIR resolves on the box.
ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${EC2_IP}" "APP_DIR='$APP_DIR' bash -s" << 'ENDSSH'
set -e
cd "$APP_DIR"
IMG=$(cat .backend_image)
# .env must already exist (created once during first-time setup — see DEPLOY-EC2.md).
# Append/refresh only the image ref so we never clobber secrets.
grep -q '^BACKEND_IMAGE=' .env && sed -i "s#^BACKEND_IMAGE=.*#BACKEND_IMAGE=$IMG#" .env || echo "BACKEND_IMAGE=$IMG" >> .env

HOST=${IMG%%/*}
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$HOST"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Nightly backup cron (idempotent). The `|| true` matters: under `set -e`, an
# empty crontab makes `grep -v` exit 1 and abort the subshell BEFORE the echo,
# which would pipe an empty crontab and silently drop the cron on a fresh box.
chmod +x "$APP_DIR/backup.sh"
( crontab -l 2>/dev/null | grep -v "$APP_DIR/backup.sh" || true; echo "0 2 * * * $APP_DIR/backup.sh >> $APP_DIR/backups/backup.log 2>&1" ) | crontab -

# TLS auto-renewal cron (idempotent). The cert was issued via certbot --standalone,
# which needs port 80 — so the hooks stop/start the nginx container around renewal.
# certbot only runs the hooks when a cert is actually due (within 30 days of expiry),
# so this is NOT nightly downtime: nginx blips ~once per 60 days at 03:00.
( crontab -l 2>/dev/null | grep -v 'certbot renew' || true; echo "0 3 * * * sudo certbot renew --quiet --standalone --pre-hook 'cd $APP_DIR && docker compose -f docker-compose.prod.yml stop nginx' --post-hook 'cd $APP_DIR && docker compose -f docker-compose.prod.yml start nginx' >> $APP_DIR/certbot-renew.log 2>&1" ) | crontab -
echo "Deployed. Containers:"; docker compose -f docker-compose.prod.yml ps
ENDSSH
echo "Done → https://$FQDN"
