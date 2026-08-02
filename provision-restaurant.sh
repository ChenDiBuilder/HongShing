#!/bin/bash
# ============================================================================
# provision-restaurant.sh — one command, profile → live isolated clone (PRD-11 / SCRUM-53)
# ----------------------------------------------------------------------------
# Turns a Restaurant Profile (profiles/<slug>.yaml) into a running, TLS-served,
# DB-seeded clone on its own EC2 box, under its own Terraform state key.
#
# Usage:
#   AWS_PROFILE=platform-demo SSH_KEY=bridgeway-portal bash provision-restaurant.sh profiles/<slug>.yaml
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

AWS_PROFILE="${AWS_PROFILE:-platform-demo}"
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
brand = p.get("branding", {}) or {}
store = p.get("storefront", {}) or {}
hours = p.get("hours", {}) or {}
loc   = p.get("locale", {}) or {}

import re
# Pre-flight gate (PRD-12 S11 / SCRUM-79): reject an obviously-malformed profile
# BEFORE any cloud resource is created. The authoritative, fuller validation runs
# in-container at seed time (app.cli.profile_validator).
_errs = []
if not (ident.get("name") or "").strip():
    _errs.append("identity.name is required")
if not (ident.get("domain") or "").strip():
    _errs.append("identity.domain is required")
_email = (owner.get("email") or "").strip()
if not _email or "@" not in _email:
    _errs.append("owner.email is required (valid email)")
_pc = brand.get("primary_color")
if _pc and not re.match(r"^#[0-9a-fA-F]{6}$", str(_pc)):
    _errs.append("branding.primary_color must be a #RRGGBB hex colour")
if _errs:
    for _e in _errs:
        sys.stderr.write(f"ERROR: {_e}\n")
    sys.exit(6)

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
emit("BRANDING_LOGO", brand.get("logo", ""))                                 # PRD-12 S4 logo pipeline
emit("STOREFRONT_ENABLED", "true" if store.get("enabled", False) else "false")  # PRD-12 S6 gating

# PRD-12 S5 (SCRUM-62): hours.open/close drive the EC2 start/stop schedule with a
# ~1h buffer (start ~1h before open, stop ~1h after close). Falls back to the
# current 9-3 ET default when hours are absent or unparseable.
_default_start, _default_stop = "cron(0 9 * * ? *)", "cron(0 15 * * ? *)"
try:
    _oh = int(str(hours["open"]).split(":")[0])
    _ch = int(str(hours["close"]).split(":")[0])
    _start_h = max(0, _oh - 1)
    _stop_h = min(23, _ch + 1)
    _start_cron = f"cron(0 {_start_h} * * ? *)"
    _stop_cron = f"cron(0 {_stop_h} * * ? *)"
except (KeyError, ValueError, IndexError, TypeError):
    _start_cron, _stop_cron = _default_start, _default_stop
emit("SCHEDULE_START_CRON", _start_cron)
emit("SCHEDULE_STOP_CRON", _stop_cron)
emit("SCHEDULE_TIMEZONE", loc.get("timezone") or "America/Toronto")
PY
)" || { echo "ERROR: failed to read profile $PROFILE" >&2; exit 1; }
eval "$PROFILE_VARS"

CERT_EMAIL="${OWNER_EMAIL:-daniel.chen@bridgewayinnovations.ca}"
[ -n "$CERT_EMAIL" ] || CERT_EMAIL="daniel.chen@bridgewayinnovations.ca"

echo "=== Provisioning '$SLUG' → https://$FQDN ==="
echo "    sms: sender='$SMS_SENDER_ID' number='$SMS_ORIGINATION_NUMBER' region='$SMS_REGION'"
echo "    owner: $OWNER_NAME <$OWNER_EMAIL>"
echo "    branding: logo='$BRANDING_LOGO'  storefront_enabled=$STOREFRONT_ENABLED"
echo "    schedule: start=$SCHEDULE_START_CRON  stop=$SCHEDULE_STOP_CRON  tz=$SCHEDULE_TIMEZONE"

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
  -var="ssh_ingress_cidr=[\"$MY_CIDR\"]" \
  -var="schedule_start_cron=$SCHEDULE_START_CRON" \
  -var="schedule_stop_cron=$SCHEDULE_STOP_CRON" \
  -var="schedule_timezone=$SCHEDULE_TIMEZONE"

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
# STOREFRONT_ENABLED (from the profile) gates whether deploy.sh builds/ships the
# storefront SPA (PRD-12 S6 / SCRUM-63).
STOREFRONT_ENABLED="$STOREFRONT_ENABLED" AWS_PROFILE="$AWS_PROFILE" SSH_KEY="$SSH_KEY" \
  bash "$HERE/deploy.sh" --app-only

# ── 4b. Logo pipeline (PRD-12 S4 / SCRUM-61) ────────────────────────────────
# An absolute branding.logo URL is seeded straight from the profile (handled in
# the seeder). A RELATIVE path is a real asset under profiles/<path>: copy it onto
# the box's customer web root so nginx serves it, and pass the served path to the
# seed via --logo-url. With no logo, LOGO_SERVED stays empty (settings.logo_url NULL).
LOGO_SERVED=""
case "$BRANDING_LOGO" in
  "" ) : ;;                                   # no logo declared
  http://*|https://* ) : ;;                   # absolute URL → seeder uses the profile value
  * )
    LOGO_SRC="$HERE/profiles/$BRANDING_LOGO"
    if [ ! -f "$LOGO_SRC" ]; then
      echo "ERROR: branding.logo '$BRANDING_LOGO' is relative but $LOGO_SRC does not exist" >&2
      exit 1
    fi
    LOGO_FILE="$(basename "$BRANDING_LOGO")"
    echo "=== Copy logo asset → box ($LOGO_FILE) ==="
    ssh "${SSH_OPTS[@]}" "ec2-user@${EC2_IP}" "mkdir -p $APP_DIR/www/customer/branding"
    scp "${SSH_OPTS[@]}" "$LOGO_SRC" "ec2-user@${EC2_IP}:$APP_DIR/www/customer/branding/$LOGO_FILE"
    LOGO_SERVED="/branding/$LOGO_FILE"
    ;;
esac

# ── 4c. Menu image assets (PRD-11 native storefront) ────────────────────────
# Per-item photos referenced by the profile's `menu:` block live under
# profiles/assets/<slug>/menu/ and are served at /menu/items/<file> — the path the
# seeder writes into menu_items.image_url. Copy them onto the box's customer web
# root. Absolute http(s) image URLs in the profile need no local asset.
MENU_ASSETS_DIR="$HERE/profiles/assets/$SLUG/menu"
if [ -d "$MENU_ASSETS_DIR" ] && [ -n "$(ls -A "$MENU_ASSETS_DIR" 2>/dev/null)" ]; then
  echo "=== Copy menu image assets → box ($(ls "$MENU_ASSETS_DIR" | wc -l | tr -d ' ') files) ==="
  ssh "${SSH_OPTS[@]}" "ec2-user@${EC2_IP}" "mkdir -p $APP_DIR/www/customer/menu/items"
  scp "${SSH_OPTS[@]}" "$MENU_ASSETS_DIR"/* "ec2-user@${EC2_IP}:$APP_DIR/www/customer/menu/items/"
fi

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
  "SLUG='$SLUG' PROFILE_BASE='$PROFILE_BASE' LOGO_SERVED='$LOGO_SERVED' bash -s" <<'ENDSSH'
set -e
CONTAINER="$SLUG-backend-1"
# Relative-logo served path (PRD-12 S4) → seeder --logo-url; empty when none/absolute.
LOGO_ARGS=""
[ -n "$LOGO_SERVED" ] && LOGO_ARGS="--logo-url $LOGO_SERVED"

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
  if docker exec "$CONTAINER" python -m app.cli seed-restaurant --profile "/tmp/$PROFILE_BASE" $LOGO_ARGS; then
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
