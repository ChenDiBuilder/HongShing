# Customer Journey

The diner's experience, start to finish — from scanning a QR code to coming back
for their reward. Everything is **phone-first** and needs **no app download**.

---

## 1. Scan the QR → land on the restaurant

A QR code on the table tent, counter, or receipt opens the restaurant's page
straight on the diner's phone. The page is branded to the restaurant (name,
colours) and shows the full menu immediately — no friction, no login wall.

![Landing page](img/01-customer-landing.png)

> **Why it matters:** the QR carries a hidden source code (`?source=table_tent`),
> so every visit is attributed to where the code lives. The owner later sees which
> placement drives the most signups.

---

## 2. Join rewards with just a phone number

Tapping **Sign In** asks only for a phone number — the entire barrier to joining
the rewards program.

![Phone number entry](img/02-customer-phone.png)

A 6-digit code is texted to the diner via SMS and entered to verify the number.
(In local development the code is logged to the backend console instead of being
sent — there is no demo bypass code.)

![Verification code](img/03-customer-otp.png)

> **Why it matters:** no email, no password, no app install. Verified signup in
> under 10 seconds — the single biggest lever on rewards-program enrolment.

---

## 3. Reward earned + browse the menu

Once verified, the diner is in the rewards program and lands on the menu. The
header now shows their account (Orders, Rewards, Account).

![Menu, signed in](img/04-customer-menu.png)

Their welcome reward is waiting under **Rewards** — here, *10% off your next order*.

![Earned reward](img/05-customer-rewards.png)

> **Why it matters:** the reward creates an immediate reason to order now and a
> reason to come back. It's configured per restaurant (offer, value, terms).

---

## 4. Order for pickup — no app needed

Tapping a dish opens its detail with a quantity picker.

![Product detail](img/06-customer-product.png)

The cart shows the order, estimated tax, total, and pickup details.

![Cart](img/07-customer-cart.png)

Placing the order confirms it instantly with an order number and pickup ETA — and
tells the diner they'll be texted updates.

![Order confirmation](img/08-customer-order-confirmation.png)

> **Why it matters:** full pickup ordering lives inside the same page the QR opened
> — the restaurant keeps the customer relationship instead of handing it (and the
> margin) to a third-party delivery app.

---

## 5. Track orders & manage the account

The diner can see their order history and reorder in one tap.

![My orders](img/09-customer-orders.png)

The account screen holds their profile and rewards.

![Account](img/10-customer-account.png)

A clear, restaurant-branded privacy page (PIPEDA-friendly) with the restaurant's
own contact details builds trust at signup.

![Privacy](img/11-customer-privacy.png)

> **Why it matters:** reorder + rewards drive repeat visits, and a transparent
> privacy story keeps phone-number collection compliant and trustworthy.
