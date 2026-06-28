# Restaurant Profiles

A **Restaurant Profile** is the single source of truth for one restaurant clone. The
platform is single-tenant per deployment (one restaurant = one isolated box + DB +
domain); a profile is everything restaurant-specific, so onboarding a new restaurant
is *write a profile → provision*, not edit code. See **PRD-11** for the full design
(`knowledge-base/prds/PRD-11-restaurant-platform-template.md`).

## Files
| File | Purpose |
|---|---|
| `restaurant.schema.json` | JSON Schema — the formal contract a profile must satisfy |
| `_template.yaml` | Blank template — copy to `<slug>.yaml` for a new restaurant |
| `hongshing.yaml` | Reference profile (the canonical example) |
| `assets/<slug>/` | Per-restaurant branding assets (logo, etc.) |

## What each section drives
| Section | Feeds |
|---|---|
| `identity` | infra names (ECR/bucket/DB/tag), the subdomain/domain, app branding |
| `branding` | logo/colors/copy on the customer + admin SPAs (via `restaurant_settings`) |
| `ordering` | the external-ordering redirect (`external_url`, `provider`) |
| `rewards` | `reward_templates` rows (the signup incentive) |
| `campaigns` | `qr_campaigns` rows + generated QR codes (source attribution) |
| `storefront.enabled` | whether the `/store` native-ordering surface is deployed |
| `sms` | SNS sender/number/region + message templates (per-restaurant origination) |
| `locale` | timezone (also the schedule timezone) + languages |
| `compliance` | PIPEDA privacy contact + CASL mailing address (required for marketing SMS) |
| `hours` | `open`/`close` drive the EC2 start/stop schedule (±1h buffer; defaults to 9am–3pm ET when unset) |
| `owner` | the initial admin (`owner` role) user |

## Domain model (demo → production)
- **Demo:** one subdomain per restaurant under a shared namespace — `<slug>.demo.bridgewayinnovations.ca`. The three surfaces are **paths** on that one host (each clone is its own box, so paths are safe): `/` customer, `/admin`, `/store`. A wildcard `*.demo.bridgewayinnovations.ca` cert covers every restaurant.
- **Cutover:** set `identity.domain` to the customer's own domain, add their DNS + cert, redeploy. Same shape, different domain — a config swap, not a re-architecture. (Cookies are host-only so the same image works on both.)

## Onboarding a new restaurant (target flow)
1. `cp profiles/_template.yaml profiles/<slug>.yaml` and fill it in (drop the logo in `assets/<slug>/`).
2. `provision-restaurant profiles/<slug>.yaml` — terraform apply (by `slug`) → build/push image → seed DB from the profile → live at `<slug>.demo.bridgewayinnovations.ca`. *(provisioner: SCRUM-53; seeder: SCRUM-50)*
3. Hand the customer the demo; at cutover, switch `identity.domain` and redeploy.

## Status
This directory currently defines the **schema + reference profile** (SCRUM-47). The
consumers — profile-driven seeder (SCRUM-50), slug-parameterized infra (SCRUM-51),
domain/routing (SCRUM-52), and the `provision-restaurant` orchestrator (SCRUM-53) —
land in subsequent stories under epic **SCRUM-46**.
