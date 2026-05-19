# HongShing — Feature Verification Guide

**Servers running**: Backend `:8500`, Customer Web `:3500`, Admin `:3501`  
**Admin credentials**: `owner@hongshing.com` / `admin123`  
**Date**: 2026-05-18

> Each feature includes exact curl commands. Copy-paste into your terminal.  
> Expected responses are shown. `✅` = verification complete.

---

## F1. Health Check

```bash
curl -s http://localhost:8500/api/health
```
**Expect**: `{"status":"ok"}`  

---

## F2. Customer OTP Auth

### 2a. Send OTP
```bash
curl -s -X POST http://localhost:8500/api/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+16475551234"}'
```
**Expect**: `{"ok":true,"message":"OTP sent"}`  
⚠ Check your backend terminal for the 6-digit OTP (printed in dev mode).

### 2b. Verify OTP (creates account, returns session cookies)
Replace `000000` with the actual OTP from step 2a.
```bash
curl -s -X POST http://localhost:8500/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+16475551234","code":"000000"}' \
  -c /tmp/hongshing-cookies.txt
```
**Expect**: JSON with `user` object containing `phone`, `role: "customer"`.  
Check cookies file: `cat /tmp/hongshing-cookies.txt` should show `access_token` and `refresh_token`.

### 2c. Refresh Token
```bash
curl -s -X POST http://localhost:8500/api/auth/refresh \
  -b /tmp/hongshing-cookies.txt -c /tmp/hongshing-cookies.txt
```
**Expect**: `{"ok":true}`  

### 2d. Wrong OTP (negative test)
```bash
curl -s -X POST http://localhost:8500/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+16475551234","code":"999999"}'
```
**Expect**: `{"detail":"Invalid or expired OTP"}` (status 401)  

---

## F3. Admin Auth

### 3a. Admin Login
```bash
curl -s -X POST http://localhost:8500/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@hongshing.com","password":"admin123"}' \
  -c /tmp/hongshing-admin-cookies.txt
```
**Expect**: JSON with `user` object containing `role: "owner"`.  

### 3b. Wrong Password (negative)
```bash
curl -s -X POST http://localhost:8500/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@hongshing.com","password":"wrong"}'
```
**Expect**: `{"detail":"Invalid email or password"}` (401)  

---

## F4. Customer Profile

### 4a. Get Profile (authenticated)
```bash
curl -s http://localhost:8500/api/customer/me \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"phone":"+16475551234","name":null,"email":null,"role":"customer",...}`  

### 4b. Update Profile
```bash
curl -s -X PATCH "http://localhost:8500/api/customer/me?name=Alice&email=alice@example.com" \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"ok":true}`  

### 4c. Profile without auth (negative)
```bash
curl -s http://localhost:8500/api/customer/me
```
**Expect**: `{"detail":"Not authenticated"}` (401)  

---

## F5. Landing Config (Public)

### 5a. Default config
```bash
curl -s http://localhost:8500/api/public/landing-config
```
**Expect**: `{"restaurant_name":"HongShing","primary_color":"#C41E3A","allow_order_without_signup":true,...}`  

### 5b. With source param (no campaign yet)
```bash
curl -s "http://localhost:8500/api/public/landing-config?source=receipt"
```
**Expect**: Same as above, `campaign: null` (no campaign created yet).

---

## F6. Admin Dashboard

```bash
curl -s http://localhost:8500/api/admin/dashboard \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"data":{"total_customers":...,"active_campaigns":...,"issued_rewards":...}}`  

Verify without auth:
```bash
curl -s http://localhost:8500/api/admin/dashboard
```
**Expect**: 401  

---

## F7. Admin Settings

### 7a. Get Settings
```bash
curl -s http://localhost:8500/api/admin/settings \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: JSON with all settings fields.

### 7b. Update Settings
```bash
curl -s -X PATCH "http://localhost:8500/api/admin/settings?restaurant_name=My%20Restaurant&primary_color=%230000FF&external_ordering_url=https://order.example.com&external_ordering_provider=toast&privacy_contact_email=privacy@example.com&support_phone=%2B16475550000" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"ok":true}`  

Verify via landing config:
```bash
curl -s http://localhost:8500/api/public/landing-config
```
**Expect**: `restaurant_name` now shows `"My Restaurant"`, `primary_color` is `"#0000FF"`.

---

## F8. QR Campaigns (Admin)

### 8a. Create Campaign
```bash
curl -s -X POST "http://localhost:8500/api/admin/qr-campaigns?name=Receipt%20QR&source_code=receipt&landing_headline=Scan%20to%20save%20%245!" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"data":{"id":"...","name":"Receipt QR","source_code":"receipt"}}`  

### 8b. Create another
```bash
curl -s -X POST "http://localhost:8500/api/admin/qr-campaigns?name=Takeout%20Bag%20QR&source_code=takeout_bag&landing_headline=Order%20direct%20next%20time!" \
  -b /tmp/hongshing-admin-cookies.txt
```

### 8c. List Campaigns
```bash
curl -s http://localhost:8500/api/admin/qr-campaigns \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Array with 2 campaigns.

### 8d. Verify landing config shows campaign
```bash
curl -s "http://localhost:8500/api/public/landing-config?source=receipt"
```
**Expect**: `campaign` is not null, has `landing_headline: "Scan to save $5!"`.

---

## F9. Reward Templates (Admin)

### 9a. Create Fixed Template
```bash
curl -s -X POST "http://localhost:8500/api/admin/reward-templates?name=%245%20Off&reward_type=fixed&reward_value=500&valid_days=30" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"data":{"id":"...","name":"$5 Off"}}`  

### 9b. Create Percentage Template
```bash
curl -s -X POST "http://localhost:8500/api/admin/reward-templates?name=10%25%20Off&reward_type=percentage&reward_value=10&valid_days=14" \
  -b /tmp/hongshing-admin-cookies.txt
```

### 9c. List Templates
```bash
curl -s http://localhost:8500/api/admin/reward-templates \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Array with 2 templates.

### 9d. Set Default Template in Settings
Use the template ID from step 9a (copy from response):
```bash
curl -s -X PATCH "http://localhost:8500/api/admin/settings?default_reward_template_id=PUT_TEMPLATE_ID_HERE" \
  -b /tmp/hongshing-admin-cookies.txt
```

---

## F10. Reward Claim (Customer)

Now that a default template exists, customers can claim real rewards.

### 10a. Claim Reward
```bash
curl -s -X POST http://localhost:8500/api/rewards/claim \
  -H "Content-Type: application/json" \
  -d '{"source_code":"receipt"}' \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"reward":{"code":"HS-XXXXXX","status":"issued",...},"short_link":"..."}`  
Note the code — it follows the `HS-` pattern with 6 Crockford Base32 characters.

### 10b. Claim Duplicate (idempotent)
```bash
curl -s -X POST http://localhost:8500/api/rewards/claim \
  -H "Content-Type: application/json" \
  -d '{"source_code":"receipt"}' \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: Same reward code as 10a (does not issue a second code for same template).

### 10c. View My Rewards
```bash
curl -s http://localhost:8500/api/customer/me/rewards \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: Array containing your reward.

---

## F11. Order Redirect

### 11a. Redirect with source (authenticated)
```bash
curl -s -X POST http://localhost:8500/api/redirects/order \
  -H "Content-Type: application/json" \
  -d '{"source_code":"receipt"}' \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"destination_url":"https://order.example.com"}` (URL from settings step 7b).

### 11b. External Order (unauthenticated)
```bash
curl -s http://localhost:8500/api/redirects/external-order
```
**Expect**: `{"destination_url":"https://order.example.com"}`  

---

## F12. Redeem Reward (Admin)

Get the reward ID from step 10a (or list all):
```bash
curl -s http://localhost:8500/api/admin/rewards \
  -b /tmp/hongshing-admin-cookies.txt
```
Copy a reward `id` with status `issued`, then:
```bash
curl -s -X PATCH "http://localhost:8500/api/admin/rewards/PUT_REWARD_ID_HERE/redeem" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"ok":true}`  

Verify the status changed:
```bash
curl -s http://localhost:8500/api/admin/rewards \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: That reward now has status `redeemed`.

---

## F13. Customer List & Detail (Admin)

### 13a. List Customers
```bash
curl -s http://localhost:8500/api/admin/customers \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Paginated list with at least 1 customer (the one from step 2b).

### 13b. Search
```bash
curl -s "http://localhost:8500/api/admin/customers?search=1647555" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Filtered results.

### 13c. Customer Detail
Copy a customer `id` from step 13a, then:
```bash
curl -s "http://localhost:8500/api/admin/customers/PUT_CUSTOMER_ID_HERE" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Full detail including `rewards`, `redirects`, and `consent` data.

---

## F14. Consent & Unsubscribe

### 14a. Opt into Marketing SMS
```bash
curl -s -X POST "http://localhost:8500/api/consent/preferences?sms_marketing_opt_in=true" \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"ok":true}`  

### 14b. Opt out
```bash
curl -s -X POST "http://localhost:8500/api/consent/preferences?sms_marketing_opt_in=false" \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: `{"ok":true}`  

### 14c. Verify consent in admin
```bash
curl -s "http://localhost:8500/api/admin/customers/PUT_CUSTOMER_ID_HERE" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `consent` object shows `sms_marketing_opt_in: false` and `unsubscribed_at` is set.

---

## F15. Admin Notifications (SMS)

### 15a. Send Transactional SMS
```bash
curl -s -X POST "http://localhost:8500/api/admin/notifications/sms?body=Your%20order%20is%20ready!&message_type=transactional" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"ok":true,"id":"..."}`  

### 15b. Send Marketing SMS (blocked by consent)
```bash
# Replace with your customer ID
CUSTOMER_ID="PUT_CUSTOMER_ID_HERE"
curl -s -X POST "http://localhost:8500/api/admin/notifications/sms?recipient_id=$CUSTOMER_ID&body=Weekend%20special!&message_type=marketing" \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: `{"detail":"Customer has not opted in to marketing SMS"}` (400) — because you opted out in F14b.

### 15c. Staff Cannot Send Notifications
```bash
# No staff account exists — skip for now.
# This verifies role-based access in tests: test_admin_crud.py line ~170
```

### 15d. List Notification History
```bash
curl -s http://localhost:8500/api/admin/notifications \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: Array with the transactional message sent in 15a.

---

## F16. QR Scan Tracking

```bash
curl -s -X POST "http://localhost:8500/api/tracking/qr-scan-confirmed?source_code=receipt&session_id=test-session-1"
```
**Expect**: `{"ok":true}`  

---

## F17. Role-Based Access

### 17a. Customer cannot access admin routes
```bash
curl -s http://localhost:8500/api/admin/dashboard \
  -b /tmp/hongshing-cookies.txt
```
**Expect**: 401 (customer cookie, not admin cookie).

### 17b. Admin cannot use customer profile
```bash
curl -s http://localhost:8500/api/customer/me \
  -b /tmp/hongshing-admin-cookies.txt
```
**Expect**: 401 (admin cookie, not customer cookie).

### 17c. Unauthenticated access blocked
```bash
curl -s http://localhost:8500/api/admin/qr-campaigns
curl -s http://localhost:8500/api/admin/reward-templates
curl -s http://localhost:8500/api/rewards/claim
```
**Expect**: All return 401.

---

## F18. UI Verification (Browser)

Open in your browser:

### Customer Web — `http://localhost:3500/?source=receipt`
- [ ] Page shows restaurant name and color from settings
- [ ] Campaign headline is visible if configured
- [ ] Enter phone → click "Send Code"
- [ ] Check backend terminal for OTP → enter it
- [ ] Reward code appears (real one from API if template configured)
- [ ] Click "Order Now" → redirects to configured external URL
- [ ] Go back → click "Order without reward" → redirects without phone entry

### Admin Web — `http://localhost:3501`
- [ ] Login with `owner@hongshing.com` / `admin123`
- [ ] Dashboard shows stat cards with actual counts
- [ ] Navigate to QR Campaigns → campaigns from F8 visible
- [ ] Navigate to Rewards → templates from F9 visible, issued rewards from F10 visible
- [ ] Redeem a reward from the Rewards page
- [ ] Navigate to Customers → search works, detail shows rewards + consent
- [ ] Navigate to Notifications → history from F15 visible, compose form works
- [ ] Navigate to Settings → values from F7 visible, edit and save works
- [ ] Sign out → returns to login

---

## Summary

| Feature | Steps | Verification |
|---------|-------|-------------|
| F1 Health | 1 curl | `{"status":"ok"}` |
| F2 Customer Auth | 4 curls | OTP sent, verified, cookie set, refresh works |
| F3 Admin Auth | 2 curls | Login works, wrong password rejected |
| F4 Customer Profile | 3 curls | Get, update, 401 without auth |
| F5 Landing Config | 2 curls | Default + campaign filter |
| F6 Admin Dashboard | 2 curls | Counts returned, blocked without auth |
| F7 Admin Settings | 3 curls | Get, update, reflected in landing config |
| F8 QR Campaigns | 4 curls | Create, list, landing config picks up |
| F9 Reward Templates | 4 curls | Create, list, set as default |
| F10 Reward Claim | 3 curls | Claim, duplicate return, view my rewards |
| F11 Order Redirect | 2 curls | Auth redirect, unauthenticated redirect |
| F12 Redeem Reward | 2 curls | Redeem, verify status changed |
| F13 Customer List | 3 curls | List, search, detail with rewards |
| F14 Consent | 3 curls | Opt in, opt out, verify in admin detail |
| F15 Notifications | 4 curls | Send, blocked by consent, history |
| F16 QR Tracking | 1 curl | Beacon accepted |
| F17 Role Access | 3 tests | Customer blocked from admin, vice versa |
| F18 UI | Browser | Full walkthrough |

All 18 features, 40+ curl commands. Start at F1 and work through sequentially.
