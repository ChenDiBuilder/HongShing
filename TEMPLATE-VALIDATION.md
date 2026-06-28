# Template Validation — does a profile-driven clone reproduce HongShing? (PRD-11 / SCRUM-54)

**Method:** static derivation, not a throwaway box. We traced every Restaurant
Profile field (`profiles/restaurant.schema.json`) through the seeder
(`backend/app/cli/seed_restaurant.py`), the provisioner (`provision-restaurant.sh`
+ `infra-ec2/`), and the runtime (`/api/...`, the 3 SPAs) to find where each value
lands — and, critically, every place a restaurant-specific value is still
**hardcoded to HongShing** so a clone would silently keep it.

**Verdict:** a clone reproduces the **core product faithfully** — phone-OTP signup,
rewards engine, QR campaigns + attribution, external-ordering redirect, admin
dashboard, per-restaurant name/colors/timezone/ordering/SMS-number/owner all come
from the profile. A handful of **secondary/cosmetic values were still hardcoded**;
the trivial ones are fixed in SCRUM-54 (below), the rest are tracked in
**PRD-12 (template completeness)** because they need a new column/migration, a
design decision, or a feature build.

## Profile → system field map

| Profile field | Lands in | Covered |
|---|---|---|
| `identity.slug` | infra (TF `slug`, state key, resource names, `<slug>-backend-1`, `/opt/<slug>`) | ✅ |
| `identity.name` | `restaurant_settings.restaurant_name`; reward `code_prefix` initials | ✅ |
| `identity.legal_name` | `restaurant_settings.legal_name` → landing-config + `/privacy` + customer footer | ✅ (SCRUM-66) |
| `identity.domain` | infra (TF `fqdn`, nginx `server_name`, LE cert, Route53, `CORS_ORIGINS`) | ✅ |
| `branding.logo` | `restaurant_settings.logo_url` — absolute URL served as-is; relative asset copied to box at provision (`/branding/<file>`) | ✅ (SCRUM-61) |
| `branding.primary_color` | `restaurant_settings.primary_color` → `/api/landing-config` → SPA | ✅ |
| `branding.secondary_color` | `restaurant_settings.secondary_color` → API (but no SPA CSS var consumes it) | ⚠️ partial |
| `branding.copy.tagline` | `restaurant_settings.tagline` → landing-config → home hero subtitle | ✅ (SCRUM-60) |
| `branding.copy.reward_success` | `restaurant_settings.reward_success_copy` → landing-config → reward screen | ✅ (SCRUM-60) |
| `ordering.external_url` | `restaurant_settings.external_ordering_url` → landing-config + redirects | ✅ |
| `ordering.provider` | `restaurant_settings.external_ordering_provider` | ✅ |
| `ordering.allow_without_signup` | `restaurant_settings.allow_order_without_signup` → landing-config | ✅ |
| `rewards[].name/type/value` | `reward_templates.*`; first reward → `default_reward_template_id` | ✅ |
| `rewards[].terms` | — (no column; `valid_days` also unsettable, always 30) | ❌ PRD-12 |
| `campaigns[].source` | `qr_campaigns.source_code` + titleized `name` | ✅ |
| `storefront.enabled` | `restaurant_settings.storefront_enabled` + gates deploy build/ship of the storefront SPA (nginx `/store/` 404s when off) | ✅ (SCRUM-63) |
| `sms.sender_id` | `.env SNS_SENDER_ID` → backend (**fixed in SCRUM-54** — was overridden by compose literal) | ✅ (SCRUM-54) |
| `sms.origination_number` | `.env` → compose → `config.sns_origination_number` | ✅ |
| `sms.region` | `.env` → compose → boto3 region (compose default now `us-east-2`) | ✅ |
| `sms.templates.otp` | `restaurant_settings.otp_sms_template` → `auth.py` OTP send (safe fallback on bad template) | ✅ (SCRUM-60) |
| `sms.templates.reward` | `restaurant_settings.reward_sms_template` → reward-issuance SMS, CASL-gated on consent + `business_mailing_address` | ✅ (SCRUM-64) |
| `locale.timezone` | `restaurant_settings.timezone` + the EC2 start/stop schedule timezone (SCRUM-62) | ✅ (SCRUM-62) |
| `locale.languages` | `restaurant_settings.languages` (CSV) → landing-config → `<html lang>` seam (plumbing only) | ✅ (SCRUM-66) |
| `compliance.privacy_contact_email` | `restaurant_settings.privacy_contact_email` → landing-config + `/privacy` | ✅ |
| `compliance.support_phone` | `restaurant_settings.support_phone` → landing-config (**added in SCRUM-54**) | ✅ (SCRUM-54) |
| `compliance.business_mailing_address` | `restaurant_settings.business_mailing_address` (seeded; CASL SMS footer use lands in SCRUM-64) | ✅ (SCRUM-66) |
| `hours.open` / `hours.close` | provision-restaurant.sh → `schedule_start_cron`/`schedule_stop_cron` (±1h buffer; defaults 9-3 ET) | ✅ (SCRUM-62) |
| `owner.email` | `users.email` (owner) + `.env OWNER_EMAIL` + certbot reg email | ✅ |
| `owner.name` | `users.name` | ✅ |

**Settings a profile cannot set today** (PRD-12 candidates): `support_phone` *(now fixed)*,
per-campaign `landing_headline`/`landing_subtitle` (admin-UI only), reward
`min_order_cents`/`max_uses_per_user`/`valid_days`.

## Fixed in SCRUM-54 (trivial, no migration, zero new decisions)

1. **SMS sender id** — `docker-compose.prod.yml` pinned `SNS_SENDER_ID: HongShing` as a
   literal, overriding the profile-derived `.env` value, so **every clone texted as
   "HongShing"**. Now `${SNS_SENDER_ID:-HongShing}` (matches the sibling vars).
2. **SMS region default** — compose default `us-east-1` → **`us-east-2`** (where the CA
   long code is out of sandbox), so a clone that omits the region lands in the right place.
3. **`hongshing.ca` order fallbacks removed** — `routes/redirects.py` and
   `routes/customer.py` (the order-redirect path) no longer fall back to
   `https://hongshing.ca/order`; an unconfigured clone returns an empty destination and
   the SPA shows an "ordering not set up" state. (Test updated.)
4. **`support_phone` now profile-driven** — added `compliance.support_phone` to the
   schema + seeder (the `restaurant_settings` column already existed); the customer SPA's
   contact line now reflects the profile.

## PRD-12 (Restaurant Template Completeness) — status

**Done:** reward code prefix (SCRUM-58), reward short-link/order host → `public_domain`
(SCRUM-59), frontend de-brand sweep incl. admin/storefront `<title>` + `secondary_color`
consume (SCRUM-65), and — this PR — `branding.copy.*` + `sms.templates.otp` (SCRUM-60),
`identity.legal_name` / `locale.languages` / `business_mailing_address` seeded (SCRUM-66),
logo asset pipeline (SCRUM-61), `storefront.enabled` gating (SCRUM-63).

**Remaining:**
- **Reward-delivery SMS** — send `sms.templates.reward` on issuance, CASL-gated on consent +
  `business_mailing_address` (SCRUM-64).
- **Reward redemption discount** — wire `calculate_discount` into checkout (SCRUM-76) + money-path tests (SCRUM-75).
- **`hours.*` → EC2 schedule** — drive the start/stop crons from the profile (SCRUM-62).
- **Per-box routing** — retire `/product-demo/hongshing`; per-clone `VITE_API_BASE` + `DEMO_PREFIX` (SCRUM-77).
- **`external_ordering_url` SPA consume** (SCRUM-78), **pre-seed profile validation** (SCRUM-79).
- **`rewards[].terms` / `valid_days` / `min_order_cents`** and `secondary_color` CSS-var consume — still profile-unsettable / partial.
- **Stale admin tests** (not a feature bug): `test_admin_crud` posted query params to
  `POST /api/admin/qr-campaigns` / `reward-templates`, which take JSON bodies — so the tests
  404'd/422'd while the admin UI (which sends JSON) works fine. Tests corrected to send bodies.

## Validation checklist (per new clone)

After `bash provision-restaurant.sh profiles/<slug>.yaml` (or local seed):

- [ ] `/api/public/landing-config` shows the clone's name, primary color, support phone, privacy email — **no "HongShing" / `#C41E3A` / `hongshing.ca`**.
- [ ] Customer signup (phone → OTP → reward) completes; reward issued.
- [ ] Admin login works with the owner from `owner.email` (temp password forces reset).
- [ ] QR campaigns exist for each `campaigns[].source`; landing `?source=<code>` attributes.
- [ ] "Order now" → the profile's `ordering.external_url` (or empty state if unset) — never `hongshing.ca`.
- [ ] SMS (if enabled) sends from the profile's `sms.sender_id` / `origination_number` in `sms.region`.
