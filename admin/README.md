# Admin

Restaurant back-office dashboard for managing customers, QR campaigns, rewards, devices, reservation slots, and notifications.

**URL:** https://d1qkx0vmdo9wnw.cloudfront.net/product-demo/hongshing-admin/

## Quick Start

```bash
npm install
npm run dev     # http://localhost:3501
npm run build   # production build to dist/
```

## Credentials

- Email: `owner@hongshing.com`
- Password: `admin123`

## Architecture

- **Vite 8** + React 19 + TypeScript 6
- **Tailwind CSS 4** via `@tailwindcss/vite`
- **State-based routing** — sidebar navigation with page state
- **API auth** — admin JWT cookies (`admin_access_token`)

## File Structure

```
src/
├── App.tsx              # Main app with sidebar nav
├── main.tsx             # React entry point
├── index.css            # Tailwind imports
├── lib/
│   └── api.ts           # Typed API wrappers
└── screens/
    ├── CustomersScreen.tsx
    ├── DashboardScreen.tsx (inline in App.tsx)
    ├── DevicesScreen.tsx
    ├── NotificationsScreen.tsx
    ├── QRCampaignsScreen.tsx
    ├── ReservationSlotsScreen.tsx
    ├── RewardsScreen.tsx
    └── SettingsScreen.tsx
```

## Dev Proxy

Vite dev server proxies `/api` to `http://localhost:8001`. In production, API calls go through CloudFront at `/product-demo/hongshing/api/admin/*`.
