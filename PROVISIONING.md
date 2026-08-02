# Provisioning a restaurant clone (PRD-11)

One command turns a Restaurant Profile into a live, isolated, TLS-served clone on
its own EC2 box, own Postgres, own domain, own SMS sender — "restaurant-in-a-box".

## Prerequisites

- A profile at `profiles/<slug>.yaml` (copy `profiles/_template.yaml`, validate
  against `profiles/restaurant.schema.json`). `identity.slug` is required.
- Local tooling: `terraform`, `python3` + PyYAML (`pip install pyyaml`), `awscli`
  logged in as the `bridgeway` profile, `docker`, `node`/`npm`.
- SSH key present at `~/.ssh/<SSH_KEY>.pem` (default `bridgeway-portal`).
- The Route 53 hosted zone `bridgewayinnovations.ca` exists (it does).

## The one command

```bash
AWS_PROFILE=platform-demo SSH_KEY=bridgeway-portal \
  bash provision-restaurant.sh profiles/<slug>.yaml
```

That's it. The script is idempotent where it matters — re-running it will not
clobber an existing `.env` (secrets/DB password are preserved) and will skip
certbot if a cert already exists.

## What it does, step by step

1. **Read the profile** (`python3` + PyYAML): `slug`, `fqdn` (from
   `identity.domain`, else `<slug>.demo.bridgewayinnovations.ca`), the `sms.*`
   block, `compliance.privacy_contact_email`, and `owner.{email,name}`. Fails
   clearly if PyYAML or the profile is missing/unparseable.
2. **Terraform** — `terraform init` against this clone's **own** remote-state key
   `<slug>/terraform.tfstate` (so clones never share state), then
   `terraform apply` with `slug`, `fqdn`, and your current IP as the SSH CIDR.
   Creates the full stack: EC2 `t4g.micro`, EIP, security group, IAM role, ECR
   repo, S3 backup bucket, the start/stop schedule, and the Route 53 A record.
3. **Bootstrap the box** (SSH): `chown` the app dir `/opt/<slug>`; create
   `/opt/<slug>/.env` **only if missing** with fresh `DB_PASSWORD`/`SECRET_KEY`
   (`openssl rand -hex 32`), `OTP_PEPPER` (`rand -hex 16`), `CORS_ORIGINS`, and
   the SMS + owner values from the profile (`chmod 600`); then issue the
   single-host Let's Encrypt cert (`certbot --standalone`, HTTP-01).
4. **Deploy** (`deploy.sh`): build + push the backend image, build the SPAs,
   ship everything to `/opt/<slug>`, render `nginx.prod.conf` for `<fqdn>`, and
   bring up the compose stack. The **storefront SPA is built/shipped only when
   `storefront.enabled: true`** (PRD-12 S6) — when off, no `www/store` dir is
   created so nginx `/store/` returns 404 (redirect-only clone).
4b. **Logo** (PRD-12 S4): if `branding.logo` is an absolute URL it is seeded
   straight onto `restaurant_settings.logo_url`. If it is a **relative path**, the
   asset must exist under `profiles/<path>`; it is copied to
   `/opt/<slug>/www/customer/branding/<file>` (served at `/branding/<file>`) and
   that served path is passed to the seed via `--logo-url`. No logo ⇒ name-only header.
5. **Seed** the DB from the profile: wait for the `<slug>-backend-1` container to
   report healthy (the schema is created by the app's startup lifespan, not
   Alembic, so seeding can't run until the backend has booted), copy the profile +
   schema onto the box and into the container, then run
   `python -m app.cli seed-restaurant --profile /tmp/<slug>.yaml [--logo-url …]`
   (settings — incl. copy/OTP template/legal/locale/storefront from PRD-12 —
   rewards, QR campaigns, owner) — retried a few times to ride out first-boot
   schema creation on a brand-new database.
6. **Print** the live URL `https://<fqdn>`.

## Cutover to a customer domain

The demo mirrors prod — same image, same shape, only the domain differs (session
cookies are host-only, so no code change is needed). To move from
`<slug>.demo.bridgewayinnovations.ca` to the customer's own domain:

1. Set `identity.domain` in `profiles/<slug>.yaml` to the customer's domain
   (e.g. `rewards.hongshing.com`).
2. Point that domain's DNS at the box's Elastic IP (an A record). If the domain
   is **not** in our Route 53 zone, create the A record at the customer's DNS
   provider; the Terraform A record only manages hosts under
   `bridgewayinnovations.ca`.
3. Re-run the one command. Terraform reuses the box (the EIP is stable), the new
   cert is issued for the new host, nginx is re-rendered, and the stack restarts
   on the customer domain. The existing `.env` and database are untouched.
