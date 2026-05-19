# HongShing — Verification Plan

**Version:** 0.2.0  
**Date:** 2026-05-18  
**Covers:** Phase 1 Foundation (scaffolding, auth, database, API contracts, QR tracking, consent)

---

## 1. Verification Layers

Following tenet T1, every feature is verified at three layers:

| Layer | Tool | Scope |
|-------|------|-------|
| Unit | pytest (Python) / vitest (TS) | Pure functions: auth service, hashing, token creation, code generation, role helpers |
| Integration | pytest + real PostgreSQL | API routes, database writes, cookies, migrations, rate limit persistence, dashboard queries |
| E2E | Playwright | Full user flows through the UI |
| Manual staging | curl + real phone | SMS copy, sender ID, SNS configuration (one-time per env) |

---

## 2. Test Categorization

### 2.1 Unit Tests (no database, no HTTP)

| Test File | Scope |
|-----------|-------|
| `test_auth_service.py` | Token encode/decode, bcrypt hash/verify round-trip, OTP hash determinism, phone hash with pepper, IP hash with pepper, temp password generation |
| `test_reward_service.py` | Crockford Base32 code generation, unique code collision retry, discount calculation (percentage, fixed), expired reward check |
| `test_consent_helpers.py` | Marketing opt-in default false, transactional vs marketing channel routing |
| `test_role_permissions.py` | owner/manager/staff/customer permission matrix, role check helper |
| `test_config.py` | Config loads from env, defaults, pydantic-settings validation |

### 2.2 Integration Tests (real PostgreSQL, Alembic schema, HTTP via ASGITransport)

| Test File | Scope |
|-----------|-------|
| `test_auth_routes.py` | send-otp → 202, verify-otp → 200 + HttpOnly cookies, wrong OTP → 401, expired OTP → 401, max attempts → 429, customer refresh flow, admin login → 200 + admin cookie |
| `test_returning_customer.py` | Valid cookie auto-recognizes user, new-browser path requires OTP, expired refresh requires re-auth, 90-day max session enforced |
| `test_middleware.py` | No cookie → 401, invalid token → 401, staff blocked from owner-only routes, customer blocked from admin routes, cookie path isolation |
| `test_qr_tracking_routes.py` | Landing page load creates page_loaded event, client beacon creates scan_confirmed event, bot-like user-agent marked is_likely_bot, repeated same-session scans deduplicated, source_code/ campaign_id preserved through funnel |
| `test_rewards_routes.py` | Claim reward creates unique code, code format HS-XXXXXX, collision retry, reward linked to source_code and campaign, claim idempotency key respected |
| `test_short_links.py` | Short link created for reward, short link created for unsubscribe, click count incremented, expired link returns 410 |
| `test_consent.py` | Marketing opt-in defaults false on signup, transactional OTP sent regardless of opt-in, marketing SMS blocked when sms_marketing_opt_in=false, unsubscribe token sets sms_marketing_opt_in=false, unsubscribe token cannot update another user |
| `test_public_routes.py` | landing-config returns defaults when no settings row, landing-config returns populated settings, source param filters campaign, privacy page accessible |
| `test_admin_routes.py` | Dashboard returns zero counts on empty DB, dashboard returns correct counts with data, dashboard blocked without auth, staff can view dashboard but not settings |
| `test_database.py` | Alembic head is current (no pending migrations), session yields and closes, all Phase 1 models present in migration output |
| `test_cli.py` | create-owner seeds user with bcrypt hash, reset-owner updates password and forces change, duplicate create is idempotent |

### 2.3 Frontend Tests (vitest + @testing-library/react)

```
customer-web/src/__tests__/
├── setup.ts                 # MSW server, render helpers
├── LandingPage.test.tsx     # Renders restaurant name/color, phone input E.164, submit calls API
├── OTPVerify.test.tsx       # 6-digit input, auto-submit on 6th digit, error on wrong code
├── RewardPage.test.tsx      # Reward code displayed, "Order Now" redirects, "Text me" button
├── ReturningCustomer.test.tsx # Cookie present → auto-recognized, no OTP needed
└── api.test.ts              # Response shape type-checking

admin/src/__tests__/
├── setup.ts
├── LoginPage.test.tsx       # Form, error on bad creds, redirect on success
├── Dashboard.test.tsx       # Sidebar renders all nav items, stat cards render zero
└── api.test.ts              # Response shape type-checking
```

### 2.4 E2E Tests (Playwright)

```
tests/e2e/
├── customer-signup.spec.ts          # QR → landing → phone → OTP → reward → redirect
├── returning-customer.spec.ts       # Sign up → close tab → reopen → recognized by cookie
├── new-browser-signup.spec.ts       # Sign up → new browser → phone+OTP → same account loads
├── admin-login.spec.ts              # Login → dashboard renders with stats
├── wrong-otp.spec.ts                # Wrong OTP shows error, no session created
└── unauthenticated-admin.spec.ts    # Direct dashboard URL redirects to login
```

**Playwright test mode OTP strategy:**
- When `APP_ENV=testing`, OTP codes are also written to a `test_sms_messages` table (plaintext, not hashed).
- Playwright reads OTP from `GET /api/test/sms-messages?phone=...` (only available when `APP_ENV=testing`).
- Do not read from `otp_codes` directly — codes are hashed in production-like envs.
- The test endpoint is disabled outside `APP_ENV=testing`.

### 2.5 Manual Staging Check (one-time per environment)

| Check | How |
|-------|-----|
| Real OTP delivery | Send OTP to approved test phone, verify SMS arrives |
| SMS copy | Verify sender ID is "HongShing", no "Reply STOP" claim |
| SNS region | Confirm messages originate from us-east-1 |

This catches SNS configuration issues that mocks cannot catch.

---

## 3. Test Database Strategy

### Per-Session Schema Setup (not per-test)

```
pytest_sessionstart:
  - Run Alembic upgrade head on test database (once)

Each test:
  - BEGIN a transaction
  - Run test assertions
  - ROLLBACK

pytest_sessionfinish:
  - No cleanup needed (transactions rolled back)
```

**Why this over create_all/drop_all per test:**
- Faster — schema is applied once, not per test.
- Closer to production — schema comes from Alembic migrations, not `Base.metadata.create_all`.
- Prevents drift between dev and test schemas.

**Test database:** `hongshing_test` (separate from dev database `hongshing`).

```bash
createdb hongshing_test
```

Environment variable override:

```
TEST_DATABASE_URL=postgresql+asyncpg://fting@localhost:5432/hongshing_test
```

**conftest.py key fixtures:**

```python
@pytest.fixture(scope="session")
def _setup_schema():
    """Run Alembic once per test session."""
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], check=True)

@pytest.fixture
async def db_session(_setup_schema):
    """Transaction-per-test, rolled back after."""
    async with engine.begin() as conn:
        await conn.begin()
        async with async_session(bind=conn) as session:
            yield session
            await conn.rollback()

@pytest.fixture
async def client(db_session):
    """HTTP test client with overridden DB dependency."""
    ...

@pytest.fixture
async def owner_user(db_session):
    """Seeds owner, returns User."""
    ...

@pytest.fixture
async def customer_user(db_session):
    """Seeds customer, returns User."""
    ...
```

---

## 4. Phase 1 Critical Lifecycle Tests

Phase 1 must prove the core customer-capture lifecycle end-to-end:

1. **New customer signup** — Scan QR, submit phone, verify OTP, receive reward, redirect to external ordering.
2. **Returning customer (same browser)** — Recognized by HttpOnly cookie, existing rewards displayed, no OTP needed.
3. **Returning customer (new browser)** — Phone + OTP re-verification, same account loaded, existing rewards visible.
4. **QR source attribution** — source_code preserved from scan → page_loaded → scan_confirmed → signup → reward.
5. **Admin visibility** — Admin can see the customer, campaign source, reward status, and redirect click in dashboard.

These five flows are the product's reason for existing. If they don't work, nothing else matters.

---

## 5. Phase 1 Features to Verify (Full Checklist)

### Backend
- [ ] Config loads from env correctly
- [ ] Database connection and session management
- [ ] All Phase 1 models present in Alembic migration
- [ ] Alembic migration is repeatable (upgrade → downgrade → upgrade)
- [ ] OTP send creates a code, rate limits enforce 1/60s and 5/hour
- [ ] OTP verify marks consumed, creates user on first login, returns tokens + cookies
- [ ] OTP verify rejects wrong code, expired code, max attempts
- [ ] Customer auth: JWT issued, HttpOnly cookies set, refresh flow works
- [ ] Admin auth: JWT issued, role validation works, wrong password rejected
- [ ] Auth middleware: protected routes reject missing/invalid/expired tokens
- [ ] Auth middleware: role-based access (staff blocked from owner-only routes)
- [ ] Returning customer: valid cookie auto-recognizes, expired refresh requires OTP re-verification
- [ ] Landing config returns restaurant settings and campaign info
- [ ] Landing config returns defaults when no settings row exists
- [ ] QR scan: page_loaded event created, scan_confirmed via beacon, bots filtered
- [ ] QR attribution: source_code preserved through full funnel
- [ ] Reward code generation: Crockford Base32, 6 chars, collision retry, unique constraint
- [ ] Consent: marketing opt-in defaults false, transactional SMS exempt
- [ ] Unsubscribe: token sets marketing opt-in false, cannot affect other user
- [ ] Short links: created for rewards/unsubscribe, click counted, expired returns 410
- [ ] Admin dashboard returns correct aggregate counts (empty and populated)
- [ ] Admin dashboard blocked without auth
- [ ] Admin owner account seeded via CLI with bcrypt hash
- [ ] Admin password reset CLI works
- [ ] Health endpoint returns 200

### Customer Web
- [ ] Landing page renders with restaurant name and primary color
- [ ] Phone number input accepts and validates E.164 format
- [ ] OTP form sends code, transitions to OTP input screen
- [ ] OTP input auto-advances on 6 digits, shows error on wrong code
- [ ] Successful OTP transitions to reward display
- [ ] Returning customer with cookie sees rewards immediately (no OTP)
- [ ] Returning customer on new browser sees phone entry, loads same account after OTP
- [ ] Reward code displayed, "Order Now" redirects to external ordering URL
- [ ] "Order without reward" escape hatch redirects without auth
- [ ] QR scan beacon fires after page render (~700ms delay)
- [ ] Error states: network failure, invalid OTP, rate limited
- [ ] `lib/api.ts` typed wrappers match backend response shapes

### Admin Web
- [ ] Login form submits credentials, redirects to dashboard on success
- [ ] Login form shows error on wrong credentials
- [ ] Dashboard shell renders sidebar navigation
- [ ] Dashboard stat cards render (even with zero counts)
- [ ] Protected routes redirect to login when unauthenticated
- [ ] `lib/api.ts` typed wrappers match backend response shapes

---

## 6. What Each Test Proves

### Backend Tests

| Test | Layer | Proves |
|------|-------|--------|
| `test_config.py` | Unit | Config reads `.env`, defaults work, `pydantic-settings` validation |
| `test_auth_service.py` | Unit | Token encode/decode round-trips, bcrypt verify rejects wrong password, OTP hash is deterministic, phone/IP hash uses pepper |
| `test_reward_service.py` | Unit | Crockford Base32 excludes O/0/I/1, collision retry works, discount calculation correct |
| `test_consent_helpers.py` | Unit | Marketing opt-in defaults false, transactional vs marketing channel routing |
| `test_role_permissions.py` | Unit | Permission matrix for owner/manager/staff/customer |
| `test_database.py` | Integration | Alembic head is current, session yields and closes |
| `test_auth_routes.py` | Integration | send-otp → 202, verify-otp → 200 + cookies, wrong OTP → 401, expired OTP → 401, max attempts → 429, refresh → new tokens, admin login → 200 + admin cookie |
| `test_returning_customer.py` | Integration | Cookie auto-recognizes, new-browser requires OTP, expired refresh requires re-auth |
| `test_middleware.py` | Integration | No cookie → 401, invalid token → 401, staff blocked from owner routes, customer blocked from admin, cookie path isolation |
| `test_qr_tracking_routes.py` | Integration | page_loaded created, scan_confirmed via beacon, bot filtering, source preserved |
| `test_rewards_routes.py` | Integration | Unique code generation, format validation, source attribution, idempotency |
| `test_short_links.py` | Integration | Link creation, click counting, expiration |
| `test_consent.py` | Integration | Opt-in defaults, transactional exempt, unsubscribe token, cross-user protection |
| `test_public_routes.py` | Integration | landing-config defaults, populated settings, campaign filtering |
| `test_admin_routes.py` | Integration | Dashboard counts, auth required, role-based visibility |
| `test_cli.py` | Integration | create-owner works, reset-owner works, idempotent duplicate create |

### Frontend Tests

| Test | Proves |
|------|--------|
| LandingPage.test.tsx | Renders restaurant name/color, phone input E.164 validation, submit calls API |
| OTPVerify.test.tsx | 6-digit input renders, auto-submit on 6th digit, error display on wrong code |
| RewardPage.test.tsx | Reward code displayed, "Order Now" redirect triggers, "Text me" button exists |
| ReturningCustomer.test.tsx | Cookie present → auto-recognized, rewards shown without OTP |
| api.test.ts (customer) | Response shapes match backend Pydantic models |
| LoginPage.test.tsx | Form renders, error on bad creds, redirect on success |
| Dashboard.test.tsx | Sidebar renders all nav items, stat cards render with zero state |
| api.test.ts (admin) | Response shapes match backend Pydantic models |

### E2E Tests

| Test | Proves |
|------|--------|
| customer-signup.spec.ts | Full flow: open landing → enter phone → read OTP from test endpoint → verify → see reward → click order redirect |
| returning-customer.spec.ts | Sign up → close tab → reopen → recognized by cookie, rewards visible |
| new-browser-signup.spec.ts | Sign up → new browser context → phone + OTP → same account loads |
| admin-login.spec.ts | Open admin → enter creds → see dashboard with stats |
| wrong-otp.spec.ts | Wrong OTP shows error, no session cookie set |
| unauthenticated-admin.spec.ts | Direct dashboard URL → redirect to login |

---

## 7. Mocking Policy

Per tenet T4: mock external dependencies, not internal modules.

| Dependency | How | Reason |
|------------|-----|--------|
| AWS SNS (OTP) | Mock `boto3.client("sns").publish` | Verify called with correct phone + message; no real SMS in tests |
| Stripe | N/A for Phase 1 | External ordering redirect only |
| HTTP | `httpx.AsyncClient(app=app, transport=ASGITransport)` | No network in route tests |
| Database | Real PostgreSQL via `hongshing_test` | No mocking; transaction-per-test isolation |
| Frontend API | MSW (`msw`) | Intercept fetch calls, return fixtures |

---

## 8. Pre-Commit Validation Checklist

Per tenet W1, before every commit:

```bash
# Backend
cd backend && source .venv/bin/activate
ruff check app/ tests/                # 0 errors
python -c "from app.main import app"  # App loads
pytest tests/ -x -q                   # All tests pass

# Frontend
cd customer-web && npx tsc --noEmit && npm run build   # Clean
npx vitest run                                           # All tests pass
cd admin && npx tsc --noEmit && npm run build            # Clean
npx vitest run                                           # All tests pass
```

---

## 9. Test Execution Order

| Step | Command | Expected Result |
|------|---------|-----------------|
| 1 | `createdb hongshing_test` | Test DB created |
| 2 | `cd backend && alembic upgrade head` | All Phase 1 tables created via migration |
| 3 | `pytest tests/ -v` | All backend unit + integration tests pass |
| 4 | `cd customer-web && npx vitest run` | All customer-web tests pass |
| 5 | `cd admin && npx vitest run` | All admin tests pass |
| 6 | Start servers with `APP_ENV=testing` | Backend on 8500, web on 3500, admin on 3501 |
| 7 | `npx playwright test` | All E2E tests pass |
| 8 | `ruff check app/ tests/` | 0 errors |
| 9 | `cd customer-web && npx tsc --noEmit` | 0 errors |
| 10 | `cd admin && npx tsc --noEmit` | 0 errors |

---

## 10. Acceptance Criteria

Phase 1 foundation is verified when:

1. All Phase 1 models are present in the Alembic migration and created in PostgreSQL.
2. Alembic upgrade → downgrade → upgrade cycle completes without errors.
3. Customer can send OTP, verify it, and receive HttpOnly session cookies.
4. Admin can log in with email/password and receive HttpOnly session cookies.
5. Protected routes reject unauthenticated requests with 401.
6. Role-based access: staff cannot access settings/promos/customer export.
7. Returning customer (valid cookie) auto-recognized — no OTP required.
8. Returning customer (new browser) can re-verify by phone and load same account.
9. QR source_code preserved from scan through signup and reward.
10. Marketing SMS blocked for users without explicit opt-in.
11. Unsubscribe token sets marketing opt-in false for correct user only.
12. Customer web app renders landing → OTP → reward screens.
13. Admin web app renders login → dashboard screens.
14. All tests pass: `pytest`, `vitest`, Playwright.
15. Lint passes: `ruff check` (0 errors), `tsc --noEmit` (0 errors).
16. Manual staging SMS check: real OTP delivered to test phone with correct sender ID.
