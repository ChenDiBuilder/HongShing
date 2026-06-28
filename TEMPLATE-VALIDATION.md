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
| `identity.legal_name` | — (read nowhere) | ❌ PRD-12 |
| `identity.domain` | infra (TF `fqdn`, nginx `server_name`, LE cert, Route53, `CORS_ORIGINS`) | ✅ |
| `branding.logo` | `restaurant_settings.logo_url` — but a **relative** path is dropped to NULL (no asset pipeline) | ❌ PRD-12 |
| `branding.primary_color` | `restaurant_settings.primary_color` → `/api/landing-config` → SPA | ✅ |
| `branding.secondary_color` | `restaurant_settings.secondary_color` → API (but no SPA CSS var consumes it) | ⚠️ partial |
| `branding.copy.tagline` | — (SPA copy hardcoded) | ❌ PRD-12 |
| `branding.copy.reward_success` | — (SPA copy hardcoded) | ❌ PRD-12 |
| `ordering.external_url` | `restaurant_settings.external_ordering_url` → landing-config + redirects | ✅ |
| `ordering.provider` | `restaurant_settings.external_ordering_provider` | ✅ |
| `ordering.allow_without_signup` | `restaurant_settings.allow_order_without_signup` → landing-config | ✅ |
| `rewards[].name/type/value` | `reward_templates.*`; first reward → `default_reward_template_id` | ✅ |
| `rewards[].terms` | — (no column; `valid_days` also unsettable, always 30) | ❌ PRD-12 |
| `campaigns[].source` | `qr_campaigns.source_code` + titleized `name` | ✅ |
| `storefront.enabled` | — (storefront always built/shipped; nothing gates it) | ❌ PRD-12 |
| `sms.sender_id` | `.env SNS_SENDER_ID` → backend (**fixed in SCRUM-54** — was overridden by compose literal) | ✅ (SCRUM-54) |
| `sms.origination_number` | `.env` → compose → `config.sns_origination_number` | ✅ |
| `sms.region` | `.env` → compose → boto3 region (compose default now `us-east-2`) | ✅ |
| `sms.templates.otp` | — (OTP body hardcoded in `auth.py`; brand name IS profile-driven) | ❌ PRD-12 |
| `sms.templates.reward` | — (no reward SMS is sent at all — missing feature) | ❌ PRD-12 |
| `locale.timezone` | `restaurant_settings.timezone` (NOT propagated to the EC2 schedule) | ⚠️ partial |
| `locale.languages` | — (no i18n) | ❌ PRD-12 |
| `compliance.privacy_contact_email` | `restaurant_settings.privacy_contact_email` → landing-config + `/privacy` | ✅ |
| `compliance.support_phone` | `restaurant_settings.support_phone` → landing-config (**added in SCRUM-54**) | ✅ (SCRUM-54) |
| `compliance.business_mailing_address` | — (CASL field, read nowhere) | ❌ PRD-12 |
| `hours.open` / `hours.close` | — (documented to drive the EC2 start/stop schedule; provisioner never reads them) | ❌ PRD-12 |
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

## Tracked for follow-up → PRD-12 (Restaurant Template Completeness)

- **Reward code prefix** still hardcoded `HS-` (`reward_service.py`) — the seeder already
  computes a per-restaurant `code_prefix`; wire it through (every clone issues `HS-…` codes today).
- **Reward short-link / order host** still `https://hongshing.ca/…` in `customer.py:167/187`
  — needs a `public_domain` column + a decision on short-link host (restaurant domain vs a
  dedicated short-link host).
- **Brand copy + SMS templating** — `branding.copy.*`, `sms.templates.otp`, and the
  (missing) reward-SMS feature; needs new columns + a CASL opt-in decision.
- **Logo asset pipeline** — relative `branding.logo` paths need a provision-time
  upload-to-served-URL step.
- **`hours.*` → EC2 schedule** — pass the profile open/close into the TF start/stop crons.
- **`storefront.enabled` gating**, **`locale.languages`/i18n**, **`identity.legal_name`**,
  **`business_mailing_address`** — currently ignored.
- **Admin/storefront `<title>`** static at build time (only customer-web updates it at runtime).
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
