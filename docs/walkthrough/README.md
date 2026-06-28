# HongShing — Product Walkthrough

A guided, screenshot-by-screenshot tour of the HongShing platform for customer
demos. The platform is three connected surfaces driven by one backend:

| Surface | Who uses it | What it does |
|---|---|---|
| **Customer web** | Diners (on their phone) | Scan a QR → join rewards in seconds → browse the menu → order for pickup → track it |
| **Admin dashboard** | Owner / manager | See acquisition + rewards analytics, manage QR campaigns, rewards, devices, settings |
| **Storefront kiosk** | Front-of-house staff | A live order queue — accept, prepare, and mark orders ready |

The whole experience comes from a **single restaurant profile** — name, colours,
rewards, QR sources, ordering link — so the same product can be stood up for any
restaurant (see [`TEMPLATE-VALIDATION.md`](../../TEMPLATE-VALIDATION.md)).

## The walkthrough

1. **[Customer journey](01-customer-journey.md)** — the QR-to-reward-to-reorder loop a diner experiences.
2. **[Admin operations](02-admin-operations.md)** — what the owner sees and controls.
3. **[Storefront kiosk](03-storefront-kiosk.md)** — how staff run the order queue.

## The pitch in one line

> Put a QR code on every table and receipt. Diners join your rewards program in
> 10 seconds with just their phone number, order pickup without an app, and come
> back for the reward — and you see exactly which table tent or receipt drove each
> signup.

## About these screenshots

Captured from a live local build (demo data, phone verification in demo mode so no
real SMS is sent). Branding, colours, rewards and QR sources are all configured
from the restaurant profile; a different restaurant would show its own. URLs that
read `localhost` are the demo environment only — a live deployment serves the
restaurant's own domain.
