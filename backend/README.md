# Backend

FastAPI backend for the HongShing restaurant platform (customer capture, ordering, reservations, rewards, admin, and storefront operations).

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
alembic upgrade head
python -m app.cli create-owner --email owner@hongshing.com --password <password>
python -m app.cli seed-menu
uvicorn app.main:app --port 8001 --reload
```

## Architecture

- **FastAPI** on port 8001
- **SQLAlchemy 2.0 async** + **asyncpg** + **PostgreSQL 16**
- **Alembic** for migrations
- **JWT** cookie-based auth (customer, admin, device)
- **AWS SNS** for SMS OTP delivery

## Route Modules

| Module | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/api/auth` | Customer OTP auth |
| `admin_auth.py` | `/api/admin/auth` | Admin login |
| `public.py` | `/api/public` | Landing config |
| `customer.py` | `/api` | Customer profile, rewards |
| `orders.py` | `/api` | Order CRUD |
| `cart.py` | `/api` | DB-backed cart |
| `menu.py` | `/api/menu` | Menu categories/items |
| `reservations.py` | `/api` | Customer reservations |
| `storefront_auth.py` | `/api/storefront/auth` | Device PIN login |
| `storefront_orders.py` | `/api/storefront` | Order queue + status updates |
| `storefront_reservations.py` | `/api/storefront` | Today's reservations |
| `admin.py` | `/api/admin` | Dashboard |
| `admin_devices.py` | `/api/admin` | Device CRUD |
| `admin_reservation_slots.py` | `/api/admin` | Slot configuration |
| `admin_qr.py` | `/api/admin` | QR campaigns |
| `admin_rewards.py` | `/api/admin` | Reward templates |
| `admin_customers.py` | `/api/admin` | Customer search |
| `admin_settings.py` | `/api/admin` | Restaurant settings |
| `tracking.py` | `/api` | QR scan beacon |
| `redirects.py` | `/api/redirects` | External order redirects |
| `test_routes.py` | `/api/test` | Test OTP retrieval |

## Models

| File | Tables |
|------|--------|
| `user.py` | users, otp_codes, otp_rate_limits, refresh_tokens |
| `campaign.py` | restaurant_settings, qr_campaigns, qr_scan_events, signup_events |
| `reward.py` | reward_templates, rewards, external_order_redirects, import_batches |
| `notification.py` | notifications, user_notification_preferences, short_links, idempotency_keys |
| `menu.py` | categories, menu_items |
| `order.py` | orders, order_items, order_status_events |
| `device.py` | devices |
| `reservation.py` | reservation_slots, reservations |
| `cart.py` | carts, cart_items |
| `test_sms.py` | test_sms_messages |

## CLI Commands

```bash
python -m app.cli create-owner --email <email> --password <pw>
python -m app.cli reset-owner --email <email>
python -m app.cli seed-menu
python -m app.cli reset-demo          # Clear all test data, keep admins
```
