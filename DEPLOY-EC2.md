# HongShing — single-box EC2 deployment

Pilot-economics deployment: **one `t4g.micro`** runs Postgres + the FastAPI
backend + nginx (which serves the three Vite SPAs). **No ALB, no RDS, no NAT.**
The box auto-starts/stops on a **profile-driven** business-hours window
(`infra-ec2/schedule.tf`): `provision-restaurant.sh` translates the profile's
`hours.open`/`hours.close` into the start/stop crons with a ~1h buffer (start ~1h
before open, stop ~1h after close), in `locale.timezone`. Defaults to **9am–3pm ET**
when `hours` is unset. (HongShing's 11:00–22:00 ⇒ box up ~10:00–23:00 ET.)

This is the cheaper alternative to the Fargate stack in `infra/` (kept as the
future upgrade path). Cost: **~$3–8/mo** + SMS usage, vs ~$37/mo for Fargate+ALB+RDS.

> **Why a bridgewayinnovations.ca subdomain, not hongshing.vela.to?**
> `vela.to` is not in this account's Route 53; `bridgewayinnovations.ca` is. So
> the hosts are `hongshing.` / `admin.hongshing.` / `store.hongshing.` `bridgewayinnovations.ca`.

## Files
| File | Role |
|---|---|
| `infra-ec2/*.tf` | EC2 + SG + EIP + IAM + ECR + S3 backups + Route53 + start/stop schedule |
| `docker-compose.prod.yml` | db + backend + nginx stack (runs on the box) |
| `nginx.prod.conf` | TLS + host routing + `/api` proxy for the 3 SPAs |
| `deploy.sh` | build/push backend, build SPAs, ship + bring up |
| `backup.sh` | nightly `pg_dump` → S3 `hongshing-db-backups-<acct>` |
| `.env.prod.example` | template for `/opt/hongshing/.env` (lives only on the box) |

## First-time provisioning
1. **Apply infra** (creates the box, EIP, ECR, backup bucket, DNS records, schedule). SSH is locked to your IP:
   ```bash
   cd infra-ec2
   MYIP=$(curl -s https://checkip.amazonaws.com)
   terraform init -backend-config="profile=platform-demo"
   terraform apply -var="ssh_ingress_cidr=[\"${MYIP}/32\"]"
   ```
2. **Create `/opt/hongshing/.env` once** (copy `.env.prod.example`, fill secrets via `openssl rand -hex 32`). Never regenerate `DB_PASSWORD` later — it's tied to the Postgres volume.
3. **Issue TLS** (DNS must resolve to the EIP first — give it a few minutes). With the stack down or port 80 free:
   ```bash
   sudo certbot certonly --standalone \
     -d hongshing.bridgewayinnovations.ca \
     -d admin.hongshing.bridgewayinnovations.ca \
     -d store.hongshing.bridgewayinnovations.ca
   # auto-renew (nginx reload hook):
   ( crontab -l; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec hongshing-nginx-1 nginx -s reload'" ) | crontab -
   ```
4. **Deploy the app**:
   ```bash
   AWS_PROFILE=platform-demo SSH_KEY=bridgeway-portal bash deploy.sh
   ```

## Routine deploys
```bash
AWS_PROFILE=platform-demo SSH_KEY=bridgeway-portal bash deploy.sh            # app + safe TF (no apply)
AWS_PROFILE=platform-demo SSH_KEY=bridgeway-portal bash deploy.sh --app-only # skip terraform
```
`deploy.sh` auto-starts the box if the schedule has it stopped.

## Notes / gotchas
- **`HARDCODED_OTP` is forced empty** in `docker-compose.prod.yml`. Never set it in prod — a value lets anyone log in with that OTP.
- The backend creates its schema on startup (`Base.metadata.create_all`), so no migration step is needed for a fresh DB. For later schema changes, use the `backend/alembic` setup.
- **`prevent_destroy` + `ignore_changes=[ami,user_data]`** guard the instance: a routine apply will not replace the box (which would wipe the DB/TLS/.env). Editing bootstrap requires a deliberate replace.
- **SPA API base URL:** the SPAs call `/api` on the same host (relative). If any app hardcodes an API URL at build time (`VITE_*`), set it before `npm run build` in `deploy.sh`.
- **DNS for `*.hongshing` is created by Terraform** in the existing `bridgewayinnovations.ca` zone — no manual Route 53 work.
- To pause cost entirely: the schedule already stops it nightly; to keep it off, `terraform apply -var="enable_business_hours_schedule=false"` and stop the instance, or set the start cron to something unreachable.
