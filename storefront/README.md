# Storefront

Restaurant operations dashboard for kitchen and front-of-house staff. Displays active orders with one-tap status updates and today's reservations.

**URL:** https://d1qkx0vmdo9wnw.cloudfront.net/product-demo/hongshing-storefront/

## Quick Start

```bash
npm install
npm run dev     # http://localhost:3502
npm run build   # production build to dist/
```

## Login

1. Create a device from the **Admin** app (Devices screen)
2. Copy the 4-digit PIN
3. Enter the PIN on the storefront login screen
4. PIN is one-time use — device becomes "paired" after first login

## Architecture

- **Vite 8** + React 19 + TypeScript 6
- **Tailwind CSS 4** via `@tailwindcss/vite`
- **10-second auto-refresh** for orders
- **Cookie-based auth** (`storefront_token` cookie)
- **Device pairing** — PIN is consumed on first use

## File Structure

```
src/
├── App.tsx              # Thin router (~80 lines)
├── main.tsx             # React entry point
├── index.css            # Tailwind imports
├── lib/
│   ├── api.ts           # API base path helper
│   └── types.ts         # Status colors/labels
└── pages/
    ├── PinLogin.tsx      # PIN entry screen
    ├── OrdersDashboard.tsx # Active orders with status buttons
    └── ReservationsView.tsx # Today's reservations
```

## Order Status Flow

```
confirmed → preparing → ready → picked_up
     ↓          ↓         ↓
  cancelled  cancelled  cancelled
```

Each status change is recorded in `order_status_events` with the device ID for audit.
