#!/bin/bash
# HongShing — manual start/stop of the EC2 box for development outside the
# 9am–3pm ET schedule. The schedule will still stop it at 3pm; use `up` to bring
# it back any time. The app stack auto-starts on boot (compose restart policy).
#
# Usage:
#   scripts/dev-box.sh up        # start the box, wait, print URLs + health
#   scripts/dev-box.sh down      # stop the box (saves compute cost)
#   scripts/dev-box.sh status    # show instance state + public IP
#   scripts/dev-box.sh ssh       # open an SSH session
#   scripts/dev-box.sh logs      # tail the app containers over SSH
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-bridgeway}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SSH_KEY="${SSH_KEY:-bridgeway-portal}"
NAME_TAG="hongshing-backend"
CUSTOMER_URL="https://hongshing.bridgewayinnovations.ca"
export AWS_PROFILE AWS_REGION

aws_() { aws --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"; }

instance_id() {
  aws_ ec2 describe-instances \
    --filters "Name=tag:Name,Values=$NAME_TAG" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].InstanceId' --output text
}

public_ip() {
  aws_ ec2 describe-instances --instance-ids "$1" \
    --query 'Reservations[].Instances[].PublicIpAddress' --output text
}

ID="$(instance_id)"
[ -n "$ID" ] && [ "$ID" != "None" ] || { echo "No instance tagged Name=$NAME_TAG found. Provision infra-ec2 first." >&2; exit 1; }

case "${1:-status}" in
  up)
    echo "Starting $ID ..."
    aws_ ec2 start-instances --instance-ids "$ID" >/dev/null
    aws_ ec2 wait instance-running --instance-ids "$ID"
    IP="$(public_ip "$ID")"
    echo "Running at $IP. Waiting for the app to answer..."
    for i in $(seq 1 30); do
      if curl -fsS --max-time 5 "$CUSTOMER_URL/api/health" >/dev/null 2>&1; then
        echo "✅ Up: $CUSTOMER_URL"; exit 0
      fi
      sleep 5
    done
    echo "⚠️  Box is running but $CUSTOMER_URL/api/health didn't respond yet (TLS/containers may still be starting)."
    ;;
  down)
    echo "Stopping $ID ..."
    aws_ ec2 stop-instances --instance-ids "$ID" >/dev/null
    echo "Stop requested. (EBS still bills ~\$1.60/mo; compute is \$0 while stopped.)"
    ;;
  status)
    aws_ ec2 describe-instances --instance-ids "$ID" \
      --query 'Reservations[].Instances[].{id:InstanceId,state:State.Name,ip:PublicIpAddress,type:InstanceType}' --output table
    ;;
  ssh)
    IP="$(public_ip "$ID")"; exec ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${IP}"
    ;;
  logs)
    IP="$(public_ip "$ID")"
    exec ssh -i ~/.ssh/${SSH_KEY}.pem "ec2-user@${IP}" \
      "cd /opt/hongshing && docker compose -f docker-compose.prod.yml logs --tail=80 -f"
    ;;
  *)
    echo "Usage: $0 {up|down|status|ssh|logs}" >&2; exit 1
    ;;
esac
