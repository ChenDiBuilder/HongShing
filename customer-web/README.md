# Customer Web

Customer-facing mobile web app for HongShing restaurant ordering and reservation system.

**URL:** https://d1qkx0vmdo9wnw.cloudfront.net/product-demo/hongshing/

## Quick Start

```bash
npm install
npm run dev     # http://localhost:3500
npm run build   # production build to dist/
```

## Architecture

- **Vite 8** + React 19 + TypeScript 6
- **Tailwind CSS 4** via `@tailwindcss/vite`
- **State-based routing** (no react-router) — pages switch via `useState<Page>`
- **DB-backed cart** — cart items persist across sessions via `/api/cart`
- **10-second polling** for order status updates

## File Structure

```
src/
├── App.tsx              # Thin router (~145 lines)
├── types.ts             # Shared types, emoji map, formatPrice
├── main.tsx             # React entry point
├── index.css            # Tailwind imports
├── context/
│   ├── api.ts           # API base path helper
│   └── CartContext.tsx  # Cart state (DB-backed via /api/cart)
├── components/
│   └── Header.tsx       # Header + Footer
└── pages/
    ├── AuthPages.tsx     # Landing, OTP verify, Reward
    ├── MenuPage.tsx      # Menu grid + Product detail
    ├── CartPage.tsx      # Cart view + Place Order
    ├── OrderPages.tsx    # Order confirmation, tracking, rewards
    └── ReservationPage.tsx # Reservations, Terms, Privacy
```

## Dev Proxy

Vite dev server proxies `/api` to `http://localhost:8001` (backend). In production, the app is served from CloudFront at `/product-demo/hongshing/` and API calls go through CloudFront's API proxy.
