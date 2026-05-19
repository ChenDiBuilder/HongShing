# HongShing — Customer Capture, Rewards & Ordering Bridge Platform

**Version:** 0.4.0  
**Date:** 2026-05-17  
**Status:** Ready for Scaffold  

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Product Strategy](#product-strategy)
3. [Customer Lifecycle](#customer-lifecycle)
4. [System Architecture](#system-architecture)
5. [Tech Stack](#tech-stack)
6. [Repository & Project Structure](#repository--project-structure)
7. [Customer Web Signup Flow](#customer-web-signup-flow)
8. [QR Code & Acquisition Strategy](#qr-code--acquisition-strategy)
9. [Existing Online Ordering Redirect Mode](#existing-online-ordering-redirect-mode)
10. [Future Native Ordering Mode](#future-native-ordering-mode)
11. [Restaurant Admin Web Dashboard](#restaurant-admin-web-dashboard)
12. [Backend API](#backend-api)
13. [Database Schema](#database-schema)
14. [Authentication & Authorization](#authentication--authorization)
15. [Reward & Promo Code System](#reward--promo-code-system)
16. [SMS & Notification Consent](#sms--notification-consent)
17. [Customer Tracking & Analytics](#customer-tracking--analytics)
18. [Background Jobs](#background-jobs)
19. [Infrastructure & AWS](#infrastructure--aws)
20. [Development Phases](#development-phases)
21. [Out of Scope for Pilot](#out-of-scope-for-pilot)
22. [Privacy & Compliance (PIPEDA)](#privacy--compliance-pipeda)
23. [Database Backup Strategy](#database-backup-strategy)
24. [Migration Path to Mobile App](#migration-path-to-mobile-app)
25. [Resolved Design Decisions](#resolved-design-decisions)

---

## Project Overview

HongShing is a restaurant-specific customer capture and engagement platform.

The pilot is designed to work **in front of the restaurant's existing online ordering page**, not replace it on day one.

The platform has two primary surfaces:

- **Customer Mobile Web Signup Page** — QR-driven landing page where customers enter a phone number, verify by OTP, claim a reward, and are redirected to the restaurant's existing online ordering page.
- **Restaurant Admin Web Dashboard** — Customer list, QR campaign tracking, signup source analytics, reward/promo code management, notification consent, and basic customer engagement tools.

The platform is single-tenant: one restaurant brand, one admin team, one customer base.

Native mobile app ordering, full internal cart/checkout, reservations, and loyalty points are deferred until the customer database and repeat-use loop are validated.

---

## Product Strategy

### Core Pilot Goal

The pilot goal is not to replace the restaurant's ordering system immediately.

The pilot goal is:

> Convert anonymous walk-in, dine-in, takeout, and online customers into known phone-number customers that the restaurant can reach again.

### Why This Matters

Many restaurants already have one or more ordering systems:

- Toast ordering page
- Square ordering page
- Uber Eats / DoorDash marketplace pages
- A custom website ordering page
- Manual phone ordering

Replacing this immediately creates operational risk.

HongShing starts as a lightweight customer relationship layer:

```text
QR code / restaurant website
→ HongShing signup page
→ phone OTP verification
→ reward issued
→ redirect to existing ordering page
→ SMS link brings customer back later
```

### Product Positioning

HongShing should be positioned to restaurant owners as:

> "We do not need to replace your ordering system yet. We help you capture repeat customers, issue rewards, and build a direct customer channel before we build deeper ordering and app features."

---

## Customer Lifecycle

### High-Level Lifecycle

```text
1. Discovery
Customer sees QR code on receipt, takeout bag, counter, table, website, or Instagram.

2. Signup
Customer scans QR and lands on a mobile web page.

3. Value Exchange
Customer is offered a simple reward, such as "$5 off your next direct pickup order."

4. Phone Capture
Customer enters phone number and verifies via SMS OTP.

5. Reward Issued
System creates a customer profile and issues a unique reward/promo code.

6. Redirect
Customer taps "Order Now" and is redirected to the restaurant's existing online ordering page.

7. Return Loop
Customer receives SMS with reward code and order link.

8. Future App Migration
When the mobile app is ready, the same phone number becomes the customer's app identity.
```

### Customer Identity Levels

#### Level 1 — Anonymous Visitor

The customer can:

- View the signup landing page.
- View offer details.
- Click "Order without reward."
- Be tracked only by source and anonymous session.

No phone number is required.

#### Level 2 — Captured Customer

The customer has verified a phone number by OTP.

The system stores:

- Phone number
- Optional first name
- Signup source
- Reward issued
- SMS consent status
- Redirect history

#### Level 3 — Returning Customer

The customer returns through:

- SMS link
- QR code
- Restaurant website
- Future mobile app

The system can recognize them by phone number and show:

- Active rewards
- Past issued codes
- Signup source
- Engagement history
- Future order/reservation history when native ordering is enabled

---

## System Architecture

### Pilot Architecture: Customer Capture + External Ordering Redirect

```text
┌─────────────────────┐
│  QR Code / Website  │
│  /claim?source=...  │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────┐
│ Customer Mobile Web Page     │
│ React / Next.js / Vite SPA   │
│                              │
│ - Landing page               │
│ - Phone signup               │
│ - OTP verification           │
│ - Reward display             │
│ - Redirect to ordering page  │
└──────────┬───────────────────┘
           │ HTTPS JSON
           ▼
┌──────────────────────────────┐
│ FastAPI Backend              │
│ ECS Fargate                  │
│                              │
│ /api/auth/*                  │
│ /api/rewards/*               │
│ /api/redirects/*             │
│ /api/admin/*                 │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ PostgreSQL / RDS             │
│                              │
│ users                        │
│ otp_codes                    │
│ qr_campaigns                 │
│ signup_events                │
│ rewards                      │
│ external_order_redirects     │
│ notification_preferences     │
└──────────────────────────────┘

External Services:
- AWS SNS for SMS OTP and transactional texts
- Existing restaurant ordering page for actual checkout
- Optional future Stripe integration for native ordering
- Optional S3/CloudFront for images and static assets
```

### Future Architecture: Native Ordering & Mobile App

The platform can later add:

- Customer mobile app
- Internal menu/cart/order flow
- Stripe PaymentIntent checkout
- Admin order queue
- Reservations
- Loyalty points/tiers
- Push notifications

The key design decision is that phone number remains the primary customer identity across both the pilot web flow and the future mobile app.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Customer Web | React + TypeScript | Mobile-first QR landing/sign-up flow |
| Admin Web App | React 18 + TypeScript | Vite SPA |
| UI Components | shadcn/ui + Radix + Tailwind CSS | Shared visual system for admin/customer web |
| Backend | Python 3.12 + FastAPI | JSON API |
| ORM | SQLAlchemy 2.0 async | With Alembic migrations |
| Database | PostgreSQL 16 | AWS RDS |
| SMS | AWS SNS | OTP, reward confirmation, order-link SMS |
| File Storage | AWS S3 | QR code images, brand assets, future menu images |
| Hosting | AWS ECS Fargate | API and worker containers |
| Background Jobs | EventBridge + SQS + ECS Worker | Cleanup, scheduled SMS, analytics refresh |
| CI/CD | GitHub Actions | Lint, test, build, deploy |
| Future Payments | Stripe | Only needed when native ordering is enabled |

---

## Repository & Project Structure

All code lives under `/HongShing/` as sub-projects:

```text
HongShing/
├── SPEC.md
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── otp.py
│   │   │   ├── qr_campaign.py
│   │   │   ├── signup_event.py
│   │   │   ├── reward.py
│   │   │   ├── redirect.py
│   │   │   ├── notification.py
│   │   │   └── admin.py
│   │   ├── schemas/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── public.py
│   │   │   ├── rewards.py
│   │   │   ├── redirects.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── reward_service.py
│   │   │   ├── qr_service.py
│   │   │   ├── redirect_service.py
│   │   │   ├── notification_service.py
│   │   │   └── analytics_service.py
│   │   ├── worker/
│   │   │   └── main.py
│   │   └── middleware/
│   │       └── auth.py
│   └── tests/
├── customer-web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   ├── ClaimPage.tsx
│       │   ├── OTPVerifyPage.tsx
│       │   ├── RewardPage.tsx
│       │   └── RedirectPage.tsx
│       ├── components/
│       ├── lib/
│       │   └── api.ts
│       └── types/
├── admin/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── screens/
│       │   ├── LoginScreen.tsx
│       │   ├── DashboardScreen.tsx
│       │   ├── CustomersScreen.tsx
│       │   ├── CustomerDetailScreen.tsx
│       │   ├── QRCampaignsScreen.tsx
│       │   ├── RewardsScreen.tsx
│       │   ├── NotificationsScreen.tsx
│       │   └── SettingsScreen.tsx
│       ├── components/
│       ├── lib/
│       │   └── api.ts
│       └── types/
├── mobile/
│   └── README.md      # Future native app placeholder
└── infra/
    ├── main.tf
    ├── ecs.tf
    ├── rds.tf
    ├── sns.tf
    ├── s3.tf
    ├── sqs.tf
    └── eventbridge.tf
```

---

## Customer Web Signup Flow

### Flow A — Claim Reward, Then Redirect

This is the primary pilot flow.

```text
Customer scans QR
→ Landing page opens
→ Customer sees reward offer
→ Customer enters phone number
→ Backend sends OTP
→ Customer verifies OTP
→ Customer profile is created or updated
→ Reward code is issued
→ Customer sees reward code
→ Customer taps "Order Now"
→ System records redirect event
→ Customer is redirected to existing online ordering page
```

### Landing Page Copy

Recommended customer-facing copy:

```text
HongShing Rewards

Order direct next time.
Get $5 off your next pickup order.

No app download needed.

[Phone number]
[Send Code]

Already have a code?
[Order Now]

[Order without reward]
```

### OTP Verification Page

```text
Enter the 6-digit code we sent you.

[ _ _ _ _ _ _ ]

[Verify]
[Resend code]
```

### Reward Success Page

```text
You're in.

Your reward code:
HS-A7K9P2

Use this code on your next direct pickup order.

[Order Now]
[Text me this code]
```

### Low-Friction Rules

- Do not require app download.
- Do not require password.
- Do not require email.
- Do not require full profile setup before reward claim.
- Ask for first name only when useful.
- Allow "Order without reward" to avoid creating a hard account wall.
- Phone number is the primary identity.
- SMS marketing opt-in must be separate from transactional SMS.

### Session Persistence & Returning Customers

**Token storage uses HttpOnly cookies, not localStorage or SecureStore.**

```
access token:   HttpOnly, Secure, SameSite=Lax, 15-minute expiry
refresh token:  HttpOnly, Secure, SameSite=Lax, 30-day rolling expiry, path=/api/auth
```

**Returning customer flow:**

```
First visit (new device/browser):
QR/SMS link → landing page → phone OTP → session created → rewards displayed

Returning visit (same device, valid cookie):
QR/SMS link → backend sees valid cookie → auto-recognized → rewards displayed immediately

Returning visit (new device, private browser, expired token):
QR/SMS link → phone entry page → OTP → existing profile loaded → rewards displayed
```

**Session limits:**
- Access token: 15 minutes.
- Refresh token: 30 days, rolling (each use extends expiry).
- Absolute session max: 90 days (after which re-auth via OTP is required).
- Re-auth required: new device, expired refresh token, or 90-day max reached.
- SMS links carry `reward_id` or `campaign_id` for context, NOT session tokens. Viewing the full reward wallet requires an active session or OTP verification.

---

## QR Code & Acquisition Strategy

### QR Placement Types

Each QR code should map to a trackable source.

| Placement | Source Code | Intent | Landing Message |
|---|---|---|---|
| Front counter | `counter` | Join rewards | "Scan to get $5 off your next pickup order." |
| Takeout bag | `takeout_bag` | Repeat order | "Order direct next time and save." |
| Receipt | `receipt` | Repeat purchase | "Use this reward on your next order." |
| Dining table | `table` | Rewards/reservations | "Join rewards. No app needed." |
| Website | `website` | Online traffic capture | "Claim your pickup reward before ordering." |
| Instagram bio | `instagram` | Social traffic | "Claim a reward before your next order." |
| Staff-assisted signup | `staff` | Manual capture | "Staff helped customer join rewards." |

### QR URL Format

```text
https://hongshing.vela.to/claim?source=receipt
https://hongshing.vela.to/claim?source=takeout_bag
https://hongshing.vela.to/claim?source=counter
```

Optionally, use short QR slugs:

```text
https://hongshing.vela.to/r/receipt
https://hongshing.vela.to/r/counter
```

### QR Code Admin Features

The admin dashboard should support:

- Create QR campaign.
- Choose source type.
- Choose landing offer.
- Generate downloadable QR image.
- Track scans.
- Track phone signups.
- Track reward claims.
- Track order redirect clicks.
- Compare QR placements.

### QR Campaign Funnel

The real funnel metric uses confirmed scans (client-side beacon), not raw server-side page loads:

```text
QR landing page loaded (server-side, for debugging)
→ QR scan confirmed (client-side beacon after ~700ms delay)
→ phone submitted
→ OTP verified
→ reward claimed
→ redirect clicked
→ SMS return clicks
```

**Why two events:** Server-side page loads include bots, crawlers, and prefetchers. The confirmed event requires a real browser rendering the page and executing JavaScript.

**Beacon implementation:**
- Page loads → waits 500–1000ms → sends `navigator.sendBeacon("/api/tracking/qr-scan-confirmed", { campaign_id, source, session_id })`.
- Backend filters obvious bots by: HEAD requests, missing JS ping, user-agent blacklist, repeated scans from same IP/session within 5 seconds.

This is the most important pilot analytics funnel.

---

## Existing Online Ordering Redirect Mode

### Purpose

Many restaurants already have an online ordering page. The pilot should use that page instead of replacing it.

HongShing acts as the customer capture and reward layer before redirecting to the existing ordering page.

### Redirect Flow

```text
Customer claims reward
→ backend issues reward code
→ frontend shows reward code
→ customer taps "Order Now"
→ backend logs redirect event
→ customer redirects to existing online ordering URL
```

### Restaurant Settings

The admin can configure:

```text
external_ordering_url = "https://hongshing.example-ordering.com"
external_ordering_provider = "toast" | "square" | "custom" | "other"
order_button_label = "Order Now"
allow_order_without_signup = true
```

### What HongShing Can Track in Redirect Mode

HongShing can track:

- Customer phone number
- Signup source
- QR placement
- Reward issued
- Redirect clicked
- SMS link clicked
- Customer return behavior
- Manual redemption if restaurant imports or marks reward used

HongShing may not know:

- What the customer ordered
- Whether the customer completed checkout
- Order total
- Item-level history
- Pickup time
- Refund status

unless the existing ordering provider supports integration, export, webhook, or manual redemption reporting.

### Order Without Reward

The landing page should include a secondary escape hatch:

```text
Order without reward
```

This prevents the QR page from becoming a hard wall before ordering.

When clicked:

- Record anonymous redirect event.
- Preserve source code.
- Redirect to existing ordering page.
- Do not create customer profile.

### Redirect URL Parameters

If the existing ordering provider supports URL parameters, append lightweight tracking:

```text
?ref=hongshing_rewards&source=receipt
```

If it supports promo prefill:

```text
?promo=HS-A7K9P2
```

If it does not support promo prefill, show the reward code clearly before redirect.

---

## Future Native Ordering Mode

Native ordering is the later version where HongShing owns the full cart, checkout, and order management flow.

### Future Flow

```text
Customer opens HongShing web/app
→ browses menu
→ adds items to cart
→ chooses pickup time
→ applies reward/promo
→ pays through Stripe
→ admin sees paid order
→ restaurant marks accepted/preparing/ready/picked_up
→ customer receives SMS/push updates
```

### Future Stripe Direction

- Restaurant owns the Stripe account and is merchant of record.
- Currency = CAD for Ontario restaurant.
- PaymentIntent created server-side.
- Webhook confirms payment.
- Reward redemption finalized only after payment success.

### Future Tables

The following tables are not needed for redirect-only pilot, but should be kept in the long-term design:

- `menu_items`
- `categories`
- `orders`
- `order_items`
- `payment_intents`
- `order_status_events`
- `reservation_slot_config`
- `reservations`

---

## Restaurant Admin Web Dashboard

### 1. Authentication

- Pre-created admin accounts only.
- Roles: `owner`, `manager`, `staff`.
- Login with email + password.
- Initial `owner` account created via CLI seed script.
- `owner` can create additional admin users.

### 2. Dashboard Home

Pilot dashboard should show:

- Signups today
- Total captured customers
- QR scans today
- Reward codes issued
- Redirect clicks
- Top QR sources
- SMS opt-in rate
- Recent customer signups

### 3. QR Campaign Management

Admin can:

- Create QR campaign.
- Set campaign name.
- Set source code.
- Assign reward offer.
- Generate QR code image.
- Download QR as PNG/SVG.
- View funnel analytics.

Example campaigns:

```text
Receipt Signup QR
Takeout Bag Signup QR
Front Counter Signup QR
Website Order Reward
Instagram Bio Reward
```

### 4. Customer Management

Admin can search customers by:

- Phone number
- Name
- Signup source
- Reward status
- SMS marketing opt-in
- Created date

Customer detail view:

- Phone
- Name
- Email optional
- Signup source
- Signup date
- Active rewards
- Reward history
- Redirect history
- SMS consent status
- Notes/manual tags

### 5. Reward & Promo Code Management

Admin can:

- Create reward templates.
- Generate unique codes.
- Assign reward to QR campaign.
- Mark reward as manually redeemed.
- Export issued codes.
- Track reward usage status.

For redirect mode, redemption can be:

- Manual: staff marks code used.
- Imported: restaurant uploads redemption CSV.
- Integrated: future provider/POS/order system sends webhook.

### 6. Notifications

Pilot notification scope:

- Transactional SMS:
  - OTP code
  - Reward code confirmation
  - Order link reminder
- Marketing SMS:
  - Only for customers with explicit opt-in
  - Admin can send simple campaign messages

Push notifications are deferred until the native app exists.

### 7. Settings

Admin can configure:

- Restaurant name
- Logo
- Brand color
- External ordering URL
- Existing ordering provider
- Default reward offer
- SMS sender label
- Timezone
- Consent copy
- Privacy/support contact

---

## Backend API

### Public Customer Routes

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/api/public/landing-config` | None | Get restaurant name, offer, branding, source config |
| `POST` | `/api/auth/send-otp` | None | Send OTP to phone number |
| `POST` | `/api/auth/verify-otp` | None | Verify OTP, create/update customer, return JWT |
| `POST` | `/api/rewards/claim` | Customer | Claim reward for source/campaign |
| `GET` | `/api/rewards/me` | Customer | List customer's active rewards |
| `POST` | `/api/redirects/order` | Optional | Record redirect click and return external ordering URL |
| `POST` | `/api/consent/preferences` | Customer | Update notification consent |
| `GET` | `/api/customer/me` | Customer | Get customer profile |
| `PATCH` | `/api/customer/me` | Customer | Update name/email |

### Admin Routes

| Method | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/api/admin/auth/login` | None | Admin email/password login |
| `POST` | `/api/admin/auth/refresh` | None | Refresh admin access token |
| `GET` | `/api/admin/dashboard` | Admin | Dashboard summary metrics |
| `GET` | `/api/admin/customers` | Admin | Search/list customers |
| `GET` | `/api/admin/customers/{id}` | Admin | Customer detail |
| `PATCH` | `/api/admin/customers/{id}` | Manager+ | Update notes/tags |
| `GET` | `/api/admin/qr-campaigns` | Admin | List QR campaigns |
| `POST` | `/api/admin/qr-campaigns` | Manager+ | Create QR campaign |
| `PATCH` | `/api/admin/qr-campaigns/{id}` | Manager+ | Update QR campaign |
| `GET` | `/api/admin/qr-campaigns/{id}/qr` | Admin | Download QR code image |
| `GET` | `/api/admin/reward-templates` | Admin | List reward templates |
| `POST` | `/api/admin/reward-templates` | Manager+ | Create reward template |
| `GET` | `/api/admin/rewards` | Admin | List issued rewards |
| `PATCH` | `/api/admin/rewards/{id}/redeem` | Staff+ | Mark reward manually redeemed |
| `POST` | `/api/admin/rewards/import-redemptions` | Manager+ | Upload CSV of redeemed codes |
| `POST` | `/api/admin/notifications/sms` | Manager+ | Send marketing SMS to opted-in customers |
| `GET` | `/api/admin/settings` | Admin | Get restaurant settings |
| `PATCH` | `/api/admin/settings` | Owner/Manager | Update settings |
| `POST` | `/api/admin/accounts` | Owner | Create admin account |

### Standard Response Envelope

All API responses use:

```json
{
  "data": {},
  "error": null
}
```

Error response:

```json
{
  "data": null,
  "error": {
    "code": "INVALID_OTP",
    "message": "The code you entered is incorrect or expired."
  }
}
```

### Pagination

List endpoints accept:

```text
?limit=50&offset=0
```

and return:

```json
{
  "data": {
    "items": [],
    "total": 142,
    "limit": 50,
    "offset": 0
  },
  "error": null
}
```

---

## Database Schema

### users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Default uuid7 |
| phone | VARCHAR(20) UNIQUE NULL | E.164 format; nullable for admin-only accounts |
| name | VARCHAR(100) NULL | Optional |
| email | VARCHAR(255) NULL | Optional for customer, required for admin |
| password_hash | VARCHAR(255) NULL | bcrypt; NULL for customer accounts |
| password_changed_at | TIMESTAMPTZ NULL | For forced password change on first login |
| role | VARCHAR(20) | `customer`, `owner`, `manager`, `staff` |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### otp_codes

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| phone | VARCHAR(20) | E.164 |
| code_hash | VARCHAR(255) | Hash of OTP |
| expires_at | TIMESTAMPTZ | Created time + 5 minutes |
| attempt_count | INTEGER | Default 0, max 5 |
| consumed | BOOLEAN | Default false |
| consumed_at | TIMESTAMPTZ NULL | |
| last_sent_at | TIMESTAMPTZ | For rate limiting |
| created_at | TIMESTAMPTZ | |

### refresh_tokens

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) | |
| token_hash | VARCHAR(255) UNIQUE | SHA-256 of token |
| expires_at | TIMESTAMPTZ | |
| revoked | BOOLEAN | Default false |
| created_at | TIMESTAMPTZ | |

### qr_campaigns

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| name | VARCHAR(100) | Example: "Receipt QR" |
| source_code | VARCHAR(50) UNIQUE | Example: `receipt`, `counter` |
| description | TEXT NULL | |
| reward_template_id | UUID NULL | FK → reward_templates |
| landing_headline | VARCHAR(200) NULL | Optional campaign-specific copy |
| landing_subtitle | VARCHAR(300) NULL | |
| active | BOOLEAN | Default true |
| created_by | UUID (FK → users) | Admin |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### qr_scan_events

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| qr_campaign_id | UUID NULL | FK → qr_campaigns |
| source_code | VARCHAR(50) | Captured from URL |
| anonymous_session_id | VARCHAR(100) | Cookie/localStorage ID |
| user_id | UUID NULL | Filled after OTP if known |
| event_type | VARCHAR(20) | `page_loaded` (server-side) or `scan_confirmed` (client-side beacon) |
| user_agent | TEXT NULL | |
| ip_hash | VARCHAR(255) NULL | Store hash only |
| is_likely_bot | BOOLEAN | Default false, set by server-side filtering |
| created_at | TIMESTAMPTZ | |

**Client-side beacon:**
```javascript
// After page render, ~700ms delay
const payload = { campaign_id, source_code, session_id };
navigator.sendBeacon("/api/tracking/qr-scan-confirmed", JSON.stringify(payload));
```

Server-side `page_loaded` events are recorded for debugging but funnel metrics use only `scan_confirmed` events. Bots are filtered by: HEAD requests, user-agent blacklist, missing JS ping, and repeated events from the same IP/session within 5 seconds.

### signup_events

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) | |
| phone | VARCHAR(20) | Snapshot |
| source_code | VARCHAR(50) NULL | |
| qr_campaign_id | UUID NULL | |
| signup_method | VARCHAR(30) | `qr`, `website`, `staff`, `manual` |
| marketing_opt_in | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### reward_templates

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| name | VARCHAR(100) | Example: "First Pickup $5 Off" |
| code_prefix | VARCHAR(10) | Example: `HS` |
| reward_type | VARCHAR(20) | `fixed`, `percentage`, `message_only` |
| reward_value | INTEGER | Cents for fixed, percentage points for percentage |
| min_order_cents | INTEGER NULL | |
| valid_days | INTEGER | Example: 30 days after issue |
| max_uses_per_user | INTEGER | Default 1 |
| active | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### rewards

Issued reward codes.

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) | |
| reward_template_id | UUID (FK → reward_templates) | |
| code | VARCHAR(50) UNIQUE | Example: `HS-A7K9P2` (Crockford Base32) |
| source_code | VARCHAR(50) NULL | |
| qr_campaign_id | UUID NULL | |
| status | VARCHAR(20) | `issued`, `redeemed`, `expired`, `cancelled` |
| issued_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ NULL | |
| redeemed_at | TIMESTAMPTZ NULL | |
| redemption_source | VARCHAR(30) NULL | `manual`, `csv_import`, `integration`, `native_order` |
| notes | TEXT NULL | |

### external_order_redirects

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID NULL | NULL if "order without reward" |
| reward_id | UUID NULL | |
| source_code | VARCHAR(50) NULL | |
| qr_campaign_id | UUID NULL | |
| destination_url | TEXT | External ordering page |
| provider | VARCHAR(50) NULL | `toast`, `square`, `custom`, `other` |
| anonymous_session_id | VARCHAR(100) NULL | |
| created_at | TIMESTAMPTZ | |

### user_notification_preferences

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users) UNIQUE | |
| sms_transactional_enabled | BOOLEAN | Default true |
| sms_marketing_opt_in | BOOLEAN | Default false |
| email_marketing_opt_in | BOOLEAN | Default false |
| push_enabled | BOOLEAN | Default false until native app |
| consent_source | VARCHAR(50) | `registration`, `admin_manual`, `api` |
| consented_at | TIMESTAMPTZ NULL | |
| unsubscribed_at | TIMESTAMPTZ NULL | |
| updated_at | TIMESTAMPTZ | |

### notifications

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| sender_id | UUID NULL | Admin who sent it |
| recipient_id | UUID NULL | NULL for campaign/broadcast |
| title | VARCHAR(200) NULL | |
| body | TEXT | |
| channel | VARCHAR(10) | `sms`, `email`, `push` |
| message_type | VARCHAR(20) | `transactional`, `marketing` |
| status | VARCHAR(20) | `draft`, `scheduled`, `sent`, `failed` |
| scheduled_at | TIMESTAMPTZ NULL | |
| sent_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |

### restaurant_settings

Singleton table.

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Fixed singleton |
| restaurant_name | VARCHAR(200) | |
| logo_url | VARCHAR(500) NULL | |
| primary_color | VARCHAR(7) | Hex |
| secondary_color | VARCHAR(7) NULL | |
| external_ordering_url | TEXT | Existing ordering page |
| external_ordering_provider | VARCHAR(50) | `toast`, `square`, `custom`, `other` |
| allow_order_without_signup | BOOLEAN | Default true |
| default_reward_template_id | UUID NULL | |
| timezone | VARCHAR(50) | Default `America/Toronto` |
| privacy_contact_email | VARCHAR(255) NULL | |
| support_phone | VARCHAR(20) NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### idempotency_keys

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| key | VARCHAR(64) | Client-supplied UUID |
| endpoint | VARCHAR(100) | |
| user_id | UUID NULL | |
| response_status | INTEGER | |
| response_body | JSONB | |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | 24h TTL |

Unique constraint on `(key, endpoint)`.

### short_links

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| code | VARCHAR(20) UNIQUE | Short code, e.g., `a7k9p2` |
| destination_url | TEXT | Full destination URL |
| link_type | VARCHAR(20) | `reward`, `redirect`, `unsubscribe` |
| user_id | UUID NULL | FK → users |
| reward_id | UUID NULL | FK → rewards |
| qr_campaign_id | UUID NULL | FK → qr_campaigns |
| expires_at | TIMESTAMPTZ NULL | |
| click_count | INTEGER | Default 0 |
| created_at | TIMESTAMPTZ | |

Short links use a branded domain (`hs.to`), not third-party shorteners (which look suspicious in SMS). Examples:

```
hs.to/r/A7K9P2           → reward detail page
hs.to/u/X8Q2             → unsubscribe page
hs.to/o/RECEIPT          → order redirect for receipt campaign
```

If `hs.to` is not yet owned, use the primary domain: `hongshing.ca/r/A7K9P2`.

### import_batches

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| import_type | VARCHAR(30) | `csv_redemption` |
| uploaded_by | UUID (FK → users) | Admin who uploaded |
| filename | VARCHAR(255) | Original filename |
| total_rows | INTEGER | |
| imported_rows | INTEGER | |
| skipped_rows | INTEGER | |
| errors | JSONB | Array of error details per row |
| created_at | TIMESTAMPTZ | |

---

## Authentication & Authorization

### Customer Auth

Customer auth uses phone number + SMS OTP. Tokens are stored as HttpOnly cookies (not localStorage or SecureStore).

Flow:

1. Customer enters phone number.
2. Backend rate-limits by phone hash and IP hash (see [Rate Limiting](#otp-rate-limiting)).
3. Backend generates 6-digit OTP.
4. OTP is stored as a hash in `otp_codes`.
5. OTP is sent by AWS SNS.
6. Customer enters OTP.
7. Backend validates OTP, marks it consumed, creates/updates customer record.
8. Backend sets `access_token` and `refresh_token` as HttpOnly, Secure, SameSite=Lax cookies.
9. Backend returns user profile data in the response body (not in the token).

### Token Configuration (Customer)

| Token | Storage | Expiry | Notes |
|-------|---------|--------|-------|
| Access | HttpOnly cookie | 15 min | `Secure`, `SameSite=Lax`, `path=/` |
| Refresh | HttpOnly cookie | 30 days rolling | `Secure`, `SameSite=Lax`, `path=/api/auth` |
| Absolute session max | — | 90 days | Re-auth via OTP required after 90 days |
| Re-auth triggers | — | — | New device, expired refresh token, 90-day max |

### Customer Session Behavior

- Returning customer on same device with valid cookie: auto-recognized, rewards displayed immediately. No OTP needed.
- Returning customer on new device: phone entry page → OTP → existing profile loaded.
- Public landing page endpoints (`/api/public/landing-config`, `/api/auth/send-otp`) are unauthenticated.
- SMS links carry `reward_id` or `campaign_id` for context, never session tokens. Full reward wallet requires auth.

### OTP Rules

- OTP length: 6 digits.
- OTP expiry: 5 minutes.
- Store only OTP hash (SHA-256), never raw OTP.
- Max verification attempts: 5 per OTP code.
- Max resend: 1 per phone per 60 seconds.
- Max sends: 5 per phone per hour.

### OTP Rate Limiting

Rate limiting is database-backed from day one (Postgres). In-memory rate limiting does not survive multi-task ECS deployments.

**otp_rate_limits table:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| phone_hash | VARCHAR(255) | SHA-256(phone + server_pepper) |
| ip_hash | VARCHAR(255) | SHA-256(ip + server_pepper) |
| window_start | TIMESTAMPTZ | Start of rate limit window |
| send_count | INTEGER | Default 0 |
| verify_attempt_count | INTEGER | Default 0 |
| last_sent_at | TIMESTAMPTZ NULL | |
| locked_until | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Unique constraint on `(phone_hash, window_start)`.

**Rate limit enforcement per OTP request:**

```
BEGIN
  upsert otp_rate_limits for phone_hash + current window
  SELECT ... FOR UPDATE
  check send_count < 5 per hour AND last_sent_at > 60s ago
  check locked_until is NULL or in the past
  increment send_count
  insert otp_codes row
COMMIT
```

- `phone_hash` and `ip_hash` are stored hashed with a server-side pepper (never raw phone or IP).
- If rate limit is exceeded, return 429 with `retry_after` seconds.
- After 5 failed verification attempts, set `locked_until` = now + 30 minutes for that phone.

**Migration path:** v0.2+ can migrate to Redis only if traffic or abuse becomes meaningful.

### Admin Auth

Admin auth uses email + password.

Roles:

- `owner`
- `manager`
- `staff`

Initial owner is seeded by CLI.

### Admin Token Configuration

| Token | Storage | Expiry | Notes |
|-------|---------|--------|-------|
| Access | HttpOnly cookie | 15 min | `Secure`, `SameSite=Lax` |
| Refresh | HttpOnly cookie | 12 hours | `Secure`, `SameSite=Lax`, `path=/api/admin/auth` |
| Idle timeout | Server-side | 30 min | Session invalidated after 30 min of inactivity |
| Absolute session max | — | 24 hours | Re-login required after 24 hours |

### Admin Re-auth Requirements

The following sensitive operations require re-authentication (current password):

- Creating admin accounts
- Exporting customer data
- Deleting/anonymizing customer records
- Changing SMS/notification settings

### Admin Account Creation

1. `owner` creates `manager` or `staff` account via admin dashboard.
2. System generates a temporary password (16 characters, cryptographically random).
3. New admin must change password on first login.
4. If admin is locked out, `owner` can reset their password from the admin dashboard.
5. If `owner` is locked out, CLI seed command resets: `python -m app.cli reset-owner --email owner@hongshing.com`.

Email-based password reset (SES) is deferred to v0.2.

### Role Permissions

| Permission | owner | manager | staff |
|---|---:|---:|---:|
| Manage settings | ✅ | ✅ | — |
| Create admin accounts | ✅ | — | — |
| View dashboard | ✅ | ✅ | ✅ |
| Manage QR campaigns | ✅ | ✅ | — |
| Manage reward templates | ✅ | ✅ | — |
| Mark reward redeemed | ✅ | ✅ | ✅ |
| View customers | ✅ | ✅ | ✅ |
| Export customers | ✅ | ✅ | — |
| Send marketing SMS | ✅ | ✅ | — |
| Update customer notes/tags | ✅ | ✅ | ✅ |

---

## Reward & Promo Code System

### Reward Template

A reward template defines the offer.

Examples:

```text
$5 off next pickup order
10% off next direct order
Free spring roll with pickup order
```

### Unique Code Generation

Each reward issued to a customer generates a unique code with the format:

```
HS-A7K9P2
```

- Prefix: `HS-`
- Random segment: 6 characters from Crockford Base32 alphabet (uppercase alphanumeric excluding `O`, `0`, `I`, `1` to avoid visual ambiguity).
- Code space: 32^6 ≈ 1.07 billion codes — sufficient for 100K codes with negligible collision risk.
- Uniqueness enforced by a database unique constraint on `rewards.code`.
- On collision, retry up to 5 times with a new random code.

**Why random, not deterministic:** Deterministic codes (e.g., derived from user_id + template_id) leak patterns and are harder to revoke or rotate. Random codes with a DB unique index are simple, safe, and support future code revocation.

### Reward Claim Rules

When a customer claims a reward:

1. Customer must verify phone number.
2. Backend checks if this customer already claimed the same reward template.
3. If not claimed, backend creates a reward code.
4. Reward is displayed on screen.
5. Reward is sent by SMS.
6. Customer can click "Order Now" to redirect.

### Redemption Tracking Modes

#### Mode 1 — Manual Redemption

Restaurant staff can search code and mark it redeemed.

Best for early pilot.

#### Mode 2 — CSV Import

Restaurant exports promo redemptions from existing ordering provider and uploads CSV.

**CSV format (minimum):**

```
code,redeemed_at,external_order_id,order_total_cents,notes
HS-A7K9P2,2026-05-17T18:30:00-04:00,ORDER-12345,4200,redeemed in existing ordering system
```

**Required column:** `code`

**Optional columns:** `redeemed_at`, `external_order_id`, `order_total_cents`, `notes`

**Import flow (three-step):**

1. **Upload** — Admin uploads CSV. Backend parses rows, validates codes exist and are not already redeemed.
2. **Preview** — Backend returns a preview showing: total rows, valid rows, rows with errors, error details per row. Admin reviews before confirming.
3. **Confirm** — Admin clicks "Import". Backend processes valid rows, skips invalid rows, returns final summary:
   ```
   Imported: 94
   Skipped: 6
   Errors:
   - Row 12: code HS-WRONG not found
   - Row 18: code HS-A3B2C1 already redeemed
   - Row 27: invalid timestamp "not-a-date"
   ```

- Skipped rows do not block valid rows. The entire file is not rejected because of one bad row.
- Each import creates an `import_batch_id` so the admin can trace or undo a bad import.
- Duplicate re-import of the same batch (same `import_batch_id`) is idempotent.

#### Mode 3 — Provider Integration

Existing ordering provider sends webhook or API data.

Best for later.

#### Mode 4 — Native Order Redemption

When HongShing owns checkout, reward redemption finalizes on payment success.

Best for future native ordering.

---

## SMS & Notification Consent

### Transactional SMS

Transactional SMS includes:

- OTP code
- Reward confirmation
- Reward/order link
- Important account messages

These are part of the service experience.

### Marketing SMS

Marketing SMS includes:

- Promotional campaigns
- Weekend specials
- Win-back offers
- New menu announcements

Marketing SMS requires explicit opt-in.

### Signup Consent Copy

Recommended checkbox:

```text
[ ] Text me occasional HongShing offers and rewards.
```

Supporting text:

```text
We will text you verification codes and reward details. Marketing offers are optional.
```

### Unsubscribe

Every marketing SMS must include a clear unsubscribe link:

```
HongShing: Your reward code is HS-A7K9P2. Order here: hs.to/r/a7k9p2
To stop offers: hs.to/u/8Kx2
```

- Unsubscribe is a web link, not "Reply STOP" — AWS SNS shared sender IDs cannot receive replies.
- The unsubscribe link opens a one-click confirmation page: "You have been unsubscribed from marketing messages."
- The system sets `unsubscribed_at` on the `user_notification_preferences` record.
- Transactional SMS (OTP, reward confirmation) are not affected by marketing unsubscribe.
- v0.2: dedicated SNS long code or third-party SMS provider for two-way SMS if needed.

---

## Customer Tracking & Analytics

### Pilot Analytics

The dashboard should focus on the acquisition funnel:

```text
QR scans
Landing page views
Phone numbers submitted
OTP verified
Rewards issued
Redirects clicked
SMS return clicks
Manual redemptions
```

### Admin Dashboard Widgets

- Signups today
- Signups this week
- Total customers captured
- Top QR source by signup
- Top QR source by redirect click
- Reward codes issued
- Reward codes redeemed
- SMS opt-in rate
- Recent signups

### Customer-Level Analytics

For each customer:

- Signup source
- Signup date
- Rewards issued
- Redirect clicks
- SMS engagement
- Manual redemption history
- Notes/tags

### Limitations in Redirect Mode

Because ordering happens externally, HongShing should not overclaim order analytics.

Unless integrated, the system does not know:

- Order total
- Menu items ordered
- Payment completion
- Pickup time
- Marketplace/provider fees

The admin UI should label redirect-mode metrics clearly as customer engagement metrics, not full revenue/order analytics.

---

## Background Jobs

### Jobs

| Job | Trigger | Notes |
|---|---|---|
| Expired OTP cleanup | Daily | Delete consumed/expired OTPs older than 24h |
| Expired reward cleanup | Hourly/daily | Mark expired rewards |
| Scheduled SMS campaign | Every 5 min | Send scheduled opted-in marketing messages |
| Analytics rollup refresh | Hourly | Update dashboard aggregates |
| Idempotency cleanup | Daily | Remove expired idempotency keys |
| Refresh token cleanup | Daily | Delete revoked/expired refresh tokens |

### Architecture

```text
EventBridge Scheduler
→ SQS Queue
→ ECS Fargate Worker
→ PostgreSQL + SNS
```

The worker shares the backend codebase but runs as a separate container entrypoint:

```text
python -m app.worker
```

---

## Infrastructure & AWS

### AWS Resources

| Resource | Service | Notes |
|---|---|---|
| API compute | ECS Fargate | FastAPI |
| Worker compute | ECS Fargate | Background jobs |
| Database | RDS PostgreSQL 16 | Customer/reward data |
| SMS | AWS SNS | OTP and SMS messages |
| Static assets | S3 + CloudFront | QR code images, branding assets |
| Domain/DNS | Route 53 | `hongshing.vela.to` or restaurant subdomain |
| SSL | ACM | TLS certificates |
| Load balancer | ALB | In front of API |
| Secrets | Secrets Manager | DB password, JWT secret, SMS settings |
| Scheduler | EventBridge | Cron triggers |
| Queue | SQS | Job dispatch |
| CI/CD | GitHub Actions | Build/test/deploy |

### AWS Authentication

Production ECS tasks use IAM task roles.

No long-lived AWS access keys should be stored in environment variables.

### Environment Variables

```text
APP_ENV=production|staging|development
SECRET_KEY=<random 64-char string>
DATABASE_URL=postgresql+asyncpg://...
CORS_ORIGINS=https://hongshing.vela.to,https://admin.hongshing.vela.to

AWS_REGION=us-east-1
S3_BUCKET=hongshing-assets
CLOUDFRONT_URL=https://cdn.hongshing.vela.to
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../jobs.fifo

SNS_SENDER_ID=HongShing

OWNER_EMAIL=owner@hongshing.com
```

---

## Development Phases

### Phase 1 — Customer Capture Foundation

- [ ] Backend scaffold
- [ ] Customer web scaffold
- [ ] Admin web scaffold
- [ ] Database models + migrations
- [ ] Phone OTP auth
- [ ] Admin email/password auth
- [ ] Restaurant settings
- [ ] Basic CI pipeline

### Phase 2 — QR Signup & Reward Claim

- [ ] QR campaign model and admin UI
- [ ] QR code generation/download
- [ ] Landing page by source
- [ ] Phone signup flow
- [ ] OTP verification
- [ ] Reward template model
- [ ] Unique reward code generation
- [ ] SMS reward confirmation

### Phase 3 — External Ordering Redirect

- [ ] External ordering URL settings
- [ ] Reward success page
- [ ] Order redirect tracking
- [ ] "Order without reward" path
- [ ] Source attribution for redirects
- [ ] Basic customer detail page

### Phase 4 — Admin Analytics & Operations

- [ ] Dashboard funnel metrics
- [ ] Customer search/list
- [ ] Customer detail view
- [ ] Manual reward redemption
- [ ] CSV redemption import
- [ ] Consent management
- [ ] Customer export

### Phase 5 — Notifications & Pilot Polish

- [ ] Marketing SMS opt-in flow
- [ ] Admin SMS campaign tool
- [ ] STOP/unsubscribe handling
- [ ] Background worker
- [ ] Analytics rollups
- [ ] Production deployment
- [ ] Printable QR assets for counter/receipt/takeout bag/table

### Phase 6 — Future Native Ordering

- [ ] Menu management
- [ ] Internal cart/order flow
- [ ] Stripe PaymentIntent integration
- [ ] Admin order queue
- [ ] Pickup status SMS
- [ ] Native mobile app
- [ ] Push notifications
- [ ] Loyalty points/tiers

---

## Out of Scope for Pilot

| Feature | Reason |
|---|---|
| Native mobile app | Phone capture should work before app download is required |
| Full internal ordering | Existing ordering page remains in place |
| Stripe checkout | Not needed until HongShing owns the order flow |
| Menu CRUD | Not needed if order page is external |
| Order item analytics | Not available unless integrated with existing ordering provider |
| Reservations | Can be added after customer capture loop works |
| Loyalty points/tiers | Start with simple reward codes first |
| Push notifications | Requires native app/device tokens |
| Delivery | Existing ordering provider handles this if available |
| POS integration | Future integration after pilot proves value |
| Multi-tenancy | Single restaurant only |

---

## Privacy & Compliance (PIPEDA)

HongShing collects phone numbers, which are personal information under PIPEDA (Personal Information Protection and Electronic Documents Act). For the pilot, the following are required from day one:

### Privacy Policy

- Public privacy policy page accessible at `/privacy`.
- Describes: what data is collected (phone number, name, signup source, reward history), why it is collected (customer rewards program), how it is used, and that it is not sold to third parties.
- Hosted as a static page served by the customer web app.

### Consent

- Near phone signup: clear language explaining what the phone number will be used for.
- Marketing SMS: separate opt-in checkbox (default unchecked).
- Consent stored in `user_notification_preferences` with `consent_source` and `consented_at` timestamps.

### Customer Data Rights

**Manual (v0.1):**

- Admin can export a single customer record as JSON via the admin dashboard.
- Admin can delete/anonymize a customer record (sets phone to hash, clears name/email, marks as anonymized).

**Self-serve (future):**

- v0.2: Customer can request their own data export or deletion via a self-serve page (requires auth).

### Data Retention

- Active customers: data retained while account is active.
- Anonymized/deleted customers: retention for 30 days for audit purposes, then hard-deleted.
- OTP codes: deleted after 24 hours.
- Expired refresh tokens: deleted after 7 days.

---

## Database Backup Strategy

### RDS Automated Backups

- **Enabled:** From day one (included in RDS cost).
- **Retention period:** 7 days for pilot, 14–30 days for production.
- **Backup window:** During restaurant off-hours (configured in Terraform).
- **Point-in-time recovery:** Enabled (transaction log backups every 5 minutes).

### Manual Snapshots

- Taken before every Alembic migration in production.
- Taken before major data operations (bulk imports, cleanup scripts).

### Deletion Protection

- RDS deletion protection enabled in production.
- Final snapshot taken on cluster deletion.

### Restore Testing

- Test restore from backup at least once before launch.
- Periodically (quarterly) verify backup integrity.

---

## Migration Path to Mobile App

The pilot intentionally collects phone numbers first because the same phone number can become the future app identity.

### Later App Flow

```text
Customer downloads app
→ enters phone number
→ verifies OTP
→ existing profile loads
→ active rewards appear
→ future order/reservation history appears
```

### Migration SMS

When the app is ready:

```text
HongShing Rewards app is ready. Your rewards are already linked to this phone number. Download here: <link>
```

### Why This Works

The customer does not need to create a new account.

The phone number becomes the durable identity across:

- QR signup
- SMS rewards
- Web ordering redirect
- Future app login
- Future native ordering
- Future loyalty

---

## Resolved Design Decisions

1. **Pilot surface** — Mobile web first, not native app first.
2. **Primary customer acquisition** — QR code signup from receipt, takeout bag, counter, table, website, Instagram, and staff-assisted flows.
3. **Signup timing** — Customer sees value first, then enters phone number to claim reward.
4. **Phone identity** — Phone number + OTP is the primary customer identity.
5. **Existing ordering page** — Pilot redirects to restaurant's existing ordering page instead of replacing it immediately.
6. **Order without reward** — Allowed as a secondary path to avoid creating a hard account wall.
7. **Reward model** — Unique per-customer reward codes (6-char Crockford Base32, random with collision retry) preferred over generic promo codes.
8. **Session storage** — HttpOnly, Secure, SameSite=Lax cookies for access (15 min) and refresh (30 days rolling, 90-day absolute max). No localStorage.
9. **Returning customers** — Auto-recognized via valid cookie. New device requires OTP re-verification. SMS links carry reward/campaign context, not session tokens.
10. **Rate limiting** — Postgres-backed `otp_rate_limits` table with phone_hash and ip_hash (hashed with server pepper). Per-window counting with row-level locks.
11. **SMS unsubscribe** — Web unsubscribe link (`hs.to/u/CODE`) in every marketing SMS. No "Reply STOP" (SNS shared sender IDs cannot receive replies).
12. **QR scan tracking** — Two events: server-side page load + client-side `sendBeacon` ping (~700ms delay). Funnel metrics use confirmed scans only. Bots filtered by user-agent, HEAD requests, and missing JS ping.
13. **CSV import** — Three-step flow: upload → preview → confirm. Row-level errors skipped with error report. `import_batch_id` for traceability.
14. **Admin password reset** — Owner/manual reset + CLI fallback. Temporary passwords, forced change on first login. No SES for v0.1.
15. **Short links** — Own branded domain (`hs.to`) with `short_links` table. No third-party shorteners.
16. **Admin sessions** — Stricter than customer: 12h refresh, 24h absolute max, 30m idle timeout. Re-auth for sensitive operations.
17. **Analytics focus** — Pilot measures customer capture and redirect funnel, not full revenue/order analytics unless integrated.
18. **Consent** — Marketing SMS requires explicit opt-in; transactional SMS is used for OTP and reward delivery. Consent stored with source and timestamp.
19. **PIPEDA compliance** — Privacy policy page, consent language, manual export/delete from day one. Self-serve portal deferred to v0.2.
20. **Database backups** — RDS automated backups (7-day retention pilot), PITR enabled, manual snapshots before migrations, deletion protection.
21. **Native app** — Future phase after phone-number customer base is built.
22. **Native ordering** — Future phase after redirect-mode pilot validates repeat customer demand.
23. **Admin dashboard** — Starts with customers, QR campaigns, rewards, consent, and funnel analytics.
24. **Security** — OTPs stored as hashes, rate-limited via Postgres, with max verification attempts and lockout.
25. **AWS credentials** — ECS task roles in production; no long-lived AWS keys in environment variables.
26. **Single tenant** — One restaurant brand, one customer base, one admin team for pilot.
