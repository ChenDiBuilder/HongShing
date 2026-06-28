#!/bin/bash
# ============================================================================
# provision-restaurant.sh — one command, profile → live isolated clone (PRD-11 / SCRUM-53)
# ----------------------------------------------------------------------------
# Turns a Restaurant Profile (profiles/<slug>.yaml) into a running, TLS-served,
# DB-seeded clone on its own EC2 box, under its own Terraform state key.
#
# Usage:
#   AWS_PROFILE=bridgeway SSH_KEY=bridgeway-portal bash provision-restaurant.sh profiles/<slug>.yaml
#
# What it does (idempotent where reasonable):
#   1. Read slug/fqdn/sms/owner/compliance from the profile (python3 + PyYAML).
#   2. terraform init (own state key <slug>/terraform.tfstate) + apply  → EC2 box + EIP + DNS.
#   3. SSH bootstrap: chown app dir; create /opt/<slug>/.env IF MISSING (fresh
#      secrets, never clobbered); issue the single-host Let's Encrypt cert.
#   4. deploy.sh — build/push backend, build SPAs, ship, bring up the compose stack.
#   5. Seed the DB from the profile via the backend CLI.
#   6. Print the live URL.
#
# Pre-reqs: terraform, python3 + PyYAML, awscli (logged in as $AWS_PROFILE),
# docker, node/npm, and ~/.ssh/$SSH_KEY.pem present. Run from the repo root.
# ============================================================================
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-bridgeway}"
AWS_REGION="us-east-1"
SSH_KEY="${SSH_KEY:-bridgeway-portal}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH_OPTS=(-i ~/.ssh/${SSH_KEY}.pem -o StrictHostKeyChecking=no)

PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
  echo "Usage: AWS_PROFILE=$AWS_PROFILE SSH_KEY=$SSH_KEY bash provision-restaurant.sh profiles/<slug>.yaml" >&2
  exit 2
fi
# Resolve the profile path (accept relative-to-repo or absolute).
case "$PROFILE" in
  /*) : ;;
  *)  PROFILE="$HERE/$PROFILE" ;;
esac
if [ ! -f "$PROFILE" ]; then
  echo "ERROR: profile not found: $PROFILE" >&2
  exit 1
fi

# ── 1. Extract profile fields (python3 + PyYAML) ────────────────────────────
# Emit shell-eval'able KEY=VALUE lines; fail clearly if PyYAML/profile is bad.
# Capture into a var first so the helper's non-zero exit (PyYAML missing, parse
# error, missing slug) propagates — `if ! eval "$(...)"` would test eval, not the
# substitution, and silently eval partial output instead of erroring.
PROFILE_VARS="$(
python3 - "$PROFILE" <<'PY'
import sys, shlex
try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML not installed — `pip install pyyaml`\n")
    sys.exit(3)
try:
    with open(sys.argv[1]) as f:
        p = yaml.safe_load(f) or {}
except Exception as e:
    sys.stderr.write(f"ERROR: cannot parse profile: {e}\n")
    sys.exit(4)

ident = p.get("identity", {}) or {}
sms   = p.get("sms", {}) or {}
comp  = p.get("compliance", {}) or {}
owner = p.get("owner", {}) or {}

slug = (ident.get("slug") or "").strip()
if not slug:
    sys.stderr.write("ERROR: identity.slug is required\n")
    sys.exit(5)

domain = (ident.get("domain") or "").strip()
fqdn   = domain if domain else f"{slug}.demo.bridgewayinnovations.ca"

def emit(k, v):
    print(f"{k}={shlex.quote(str(v if v is not None else ''))}")

emit("SLUG", slug)
emit("FQDN", fqdn)
emit("SMS_SENDER_ID", sms.get("sender_id", ""))
emit("SMS_ORIGINATION_NUMBER", sms.get("origination_number", ""))
emit("SMS_REGION", sms.get("region", "us-east-2"))  # CA long code lives in us-east-2
emit("PRIVACY_CONTACT_EMAIL", comp.get("privacy_contact_email", ""))
emit("OWNER_EMAIL", owner.get("email", ""))
emit("OWNER_NAME", owner.get("name", ""))
PY
)" || { echo "ERROR: failed to read profile $PROFILE" >&2; exit 1; }
eval "$PROFILE_VARS"

CERT_EMAIL="${OWNER_EMAIL:-daniel.chen@bridgewayinnovations.ca}"
[ -n "$CERT_EMAIL" ] || CERT_EMAIL="daniel.chen@bridgewayinnovations.ca"

echo "=== Provisioning '$SLUG' → https://$FQDN ==="
echo "    sms: sender='$SMS_SENDER_ID' number='$SMS_ORIGINATION_NUMBER' region='$SMS_REGION'"
echo "    owner: $OWNER_NAME <$OWNER_EMAIL>"

# ── 2. Terraform: own state key, apply the box ──────────────────────────────
echo "=== terraform init + apply (state key: $SLUG/terraform.tfstate) ==="
cd "$HERE/infra-ec2"
terraform init \
  -backend-config="profile=$AWS_PROFILE" \
  -backend-config="key=$SLUG/terraform.tfstate" \
  -reconfigure

MY_CIDR="$(curl -s https://checkip.amazonaws.com)/32"
terraform apply -auto-approve \
  -var="slug=$SLUG" \
  -var="fqdn=$FQDN" \
  -var="ssh_ingress_cidr=[\"$MY_CIDR\"]"

EC2_IP=$(terraform output -raw ec2_public_ip)
echo "EC2 EIP: $EC2_IP"

# ── 3. SSH bootstrap: app-dir ownership, .env (if missing), TLS cert ─────────
APP_DIR="/opt/$SLUG"
echo "=== Bootstrap box: chown $APP_DIR, create .env (if missing), issue cert ==="

# Wait for SSH to come up (a fresh box needs a moment).
for i in $(seq 1 30); do
  if ssh "${SSH_OPTS[@]}" -o ConnectTimeout=5 "ec2-user@${EC2_IP}" true 2>/dev/null; then break; fi
  echo "  waiting for SSH ($i/30)..."; sleep 10
done

ssh "${SSH_OPTS[@]}" "ec2-user@${EC2_IP}" \
  "APP_DIR='$APP_DIR' FQDN='$FQDN' CERT_EMAIL='$CERT_EMAIL' \
   SMS_SENDER_ID='$SMS_SENDER_ID' SMS_ORIGINATION_NUMBER='$SMS_ORIGINATION_NUMBER' \
   SMS_REGION='$SMS_REGION' OWNER_EMAIL='$OWNER_EMAIL' FQDN_ORIGIN='https://$FQDN' \
   bash -s" <<'ENDSSH'
set -e
sudo chown -R ec2-user:ec2-user "$APP_DIR"
mkdir -p "$APP_DIR"

# Create .env ONCE — never clobber existing secrets (DB_PASSWORD must match the
# Postgres volume for the life of the box).
if [ ! -f "$APP_DIR/.env" ]; then
  echo "  creating fresh $APP_DIR/.env"
  umask 077
  cat > "$APP_DIR/.env" <<EOF
DB_PASSWORD=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
OTP_PEPPER=$(openssl rand -hex 16)
CORS_ORIGINS=$FQDN_ORIGIN
SNS_SENDER_ID=$SMS_SENDER_ID
SNS_ORIGINATION_NUMBER=$SMS_ORIGINATION_NUMBER
SNS_REGION=$SMS_REGION
OWNER_EMAIL=$OWNER_EMAIL
EOF
  chmod 600 "$APP_DIR/.env"
else
  echo "  $APP_DIR/.env already exists — leaving secrets untouched"
fi

# Issue the single-host Let's Encrypt cert (HTTP-01, standalone). nginx (if up)
# holds :80, so stop the compose stack briefly for the standalone challenge.
# A trap guarantees nginx comes back even if certbot fails or the shell aborts —
# otherwise a re-run against an already-live box could leave the site down.
restore_nginx() {
  [ -f "$APP_DIR/docker-compose.prod.yml" ] && \
    ( cd "$APP_DIR" && docker compose -f docker-compose.prod.yml start nginx 2>/dev/null || true )
}
if [ ! -d "/etc/letsencrypt/live/$FQDN" ]; then
  echo "  issuing cert for $FQDN"
  if [ -f "$APP_DIR/docker-compose.prod.yml" ]; then
    trap restore_nginx EXIT
    ( cd "$APP_DIR" && docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true )
  fi
  sudo certbot certonly --standalone --non-interactive --agree-tos \
    -m "$CERT_EMAIL" -d "$FQDN"
else
  echo "  cert for $FQDN already present — skipping certbot"
fi
ENDSSH

# ── 4. Deploy: build/push backend, build SPAs, ship, bring up the stack ──────
echo "=== deploy.sh (build + push + ship + up; renders nginx for $FQDN) ==="
cd "$HERE"
AWS_PROFILE="$AWS_PROFILE" SSH_KEY="$SSH_KEY" bash "$HERE/deploy.sh" --app-only

# ── 5. Seed the DB from the profile ─────────────────────────────────────────
# On a fresh box the schema is created by the FastAPI startup lifespan
# (Base.metadata.create_all), NOT Alembic — so it lands only after the backend
# boots and first-time Postgres init finishes. Wait for the container to be
# healthy, then retry the seed to ride out the create_all tail; seeding too early
# would hit "relation does not exist" and leave the clone with no owner login.
echo "=== Seed restaurant data from the profile ==="
PROFILE_BASE="$(basename "$PROFILE")"
scp "${SSH_OPTS[@]}" "$PROFILE" "$HERE/profiles/restaurant.schema.json" \
  "ec2-user@${EC2_IP}:/tmp/"
ssh "${SSH_OPTS[@]}" "ec2-user@${EC2_IP}" \
  "SLUG='$SLUG' PROFILE_BASE='$PROFILE_BASE' bash -s" <<'ENDSSH'
set -e
CONTAINER="$SLUG-backend-1"

# Wait for the backend container to report healthy (Dockerfile HEALTHCHECK has a
# 30s start-period). Falls through on "running" for images without a healthcheck.
echo "  waiting for $CONTAINER to be ready..."
for i in $(seq 1 40); do   # up to ~200s
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || echo missing)"
  if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
    echo "    $CONTAINER: $status (try $i)"; break
  fi
  echo "    $CONTAINER: $status ($i/40)"; sleep 5
done

docker cp "/tmp/$PROFILE_BASE"            "$CONTAINER:/tmp/$PROFILE_BASE"
docker cp "/tmp/restaurant.schema.json"   "$CONTAINER:/tmp/restaurant.schema.json"

# Retry the seed: even once healthy, create_all may still be finishing on a brand-
# new DB, so tolerate a transient "relation does not exist".
seeded=""
for i in $(seq 1 10); do
  if docker exec "$CONTAINER" python -m app.cli seed-restaurant --profile "/tmp/$PROFILE_BASE"; then
    seeded=1; break
  fi
  echo "  seed attempt $i failed (schema may still be initializing); retrying in 5s..."; sleep 5
done
[ -n "$seeded" ] || { echo "ERROR: seed-restaurant failed after retries" >&2; exit 1; }
ENDSSH

# ── 6. Done ─────────────────────────────────────────────────────────────────
echo ""
echo "=== '$SLUG' is live ==="
echo "    https://$FQDN"
