#!/usr/bin/env bash
# HongShing — Integration Test Suite
# Verifies customer-web, admin, and storefront work together end-to-end.
# Usage: bash tests/integration.sh
set -euo pipefail

BASE="https://d1qkx0vmdo9wnw.cloudfront.net/product-demo/hongshing"
PASS=0
FAIL=0
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { PASS=$((PASS + 1)); printf "${GREEN}PASS${NC} %s\n" "$1"; }
fail() { FAIL=$((FAIL + 1)); printf "${RED}FAIL${NC} %s — %s\n" "$1" "$2"; }

# ---------- helpers ----------
get_otp() {
  echo "111111"
}

admin_login() {
  curl -s -c /tmp/hs_test_admin.txt -X POST "${BASE}/api/admin/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"owner@hongshing.com","password":"admin123"}' > /dev/null
}

# ---------- Scenario 1: Customer places order, storefront sees it ----------
echo ""
printf "${CYAN}═══ Scenario 1: Order → Storefront → Admin Dashboard ═══${NC}\n"

TEST_PHONE="+16475550000"
SHORT_PHONE="6475550000"

# 1a — health check
echo -n ""
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/api/health")
[ "$HTTP" = "200" ] && pass "Backend health returns 200" || fail "Backend health" "got $HTTP"

# 1b — send OTP
SEND=$(curl -s -X POST "${BASE}/api/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"${TEST_PHONE}\"}")
[ "$(echo "$SEND" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))" 2>/dev/null)" = "True" ] \
  && pass "OTP sent to $TEST_PHONE" \
  || fail "OTP send" "$SEND"

# 1c — retrieve OTP
sleep 1
OTP=$(get_otp "$SHORT_PHONE")
[ -n "$OTP" ] && pass "OTP retrieved: $OTP" || fail "OTP retrieval" "empty"

# 1d — verify OTP, get customer session
VERIFY=$(curl -s -c /tmp/hs_test_cust.txt -X POST "${BASE}/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"${TEST_PHONE}\",\"code\":\"${OTP}\"}")
CUST_ID=$(echo "$VERIFY" | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['id'])" 2>/dev/null)
[ -n "$CUST_ID" ] && pass "Customer signed up: $CUST_ID" || fail "Customer signup" "$VERIFY"

# 1e — customer places order
ORDER=$(curl -s -b /tmp/hs_test_cust.txt -X POST "${BASE}/api/orders" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"menu_item_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567890","name":"Kung Pao Chicken","price_cents":1695,"quantity":2},{"menu_item_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567891","name":"Wonton Soup","price_cents":895,"quantity":1}]}')
ORDER_ID=$(echo "$ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('order_id',''))" 2>/dev/null)
ORDER_STATUS=$(echo "$ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
[ "$ORDER_STATUS" = "confirmed" ] && pass "Order created: $ORDER_ID (status=$ORDER_STATUS)" \
  || fail "Order creation" "$ORDER"

# 1f — admin dashboard reflects order
admin_login
DASH=$(curl -s -b /tmp/hs_test_admin.txt "${BASE}/api/admin/dashboard")
TOTAL_ORDERS=$(echo "$DASH" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['total_orders'])" 2>/dev/null)
[ "$TOTAL_ORDERS" -ge 1 ] && pass "Admin dashboard: total_orders=$TOTAL_ORDERS" \
  || fail "Admin dashboard" "$DASH"

# 1g — customer can see their order
CUST_ORDER=$(curl -s -b /tmp/hs_test_cust.txt "${BASE}/api/customer/me/orders/${ORDER_ID}")
CUST_STATUS=$(echo "$CUST_ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin)['order']['status'])" 2>/dev/null)
[ "$CUST_STATUS" = "confirmed" ] && pass "Customer sees order status: $CUST_STATUS" \
  || fail "Customer order view" "$CUST_ORDER"

# ---------- Scenario 2: Storefront login, process order, customer sees updates ----------
echo ""
printf "${CYAN}═══ Scenario 2: Storefront processes order ═══${NC}\n"

# 2a — admin creates device
DEVICE=$(curl -s -b /tmp/hs_test_admin.txt -X POST "${BASE}/api/admin/devices" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Kitchen","location":"Kitchen"}')
DEVICE_PIN=$(echo "$DEVICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['pin'])" 2>/dev/null)
[ -n "$DEVICE_PIN" ] && pass "Device created, PIN=$DEVICE_PIN" || fail "Device creation" "$DEVICE"

# 2b — storefront login with PIN
SF_LOGIN=$(curl -s -c /tmp/hs_test_sf.txt -X POST "${BASE}/api/storefront/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"pin\":\"${DEVICE_PIN}\"}")
SF_DEVICE=$(echo "$SF_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['device']['name'])" 2>/dev/null)
[ "$SF_DEVICE" = "Test Kitchen" ] && pass "Storefront logged in: $SF_DEVICE" \
  || fail "Storefront login" "$SF_LOGIN"

# 2c — device is now paired
DEVICES=$(curl -s -b /tmp/hs_test_admin.txt "${BASE}/api/admin/devices")
DEV_STATUS=$(echo "$DEVICES" | python3 -c "import sys,json; d=json.load(sys.stdin); print([x['status'] for x in d['data'] if x['name']=='Test Kitchen'][0])" 2>/dev/null)
[ "$DEV_STATUS" = "paired" ] && pass "Device status is 'paired'" \
  || fail "Device pairing" "status=$DEV_STATUS"

# 2d — storefront sees the order
SF_ORDERS=$(curl -s -b /tmp/hs_test_sf.txt "${BASE}/api/storefront/orders")
SF_ORDER_ID=$(echo "$SF_ORDERS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['orders'][-1]['id'])" 2>/dev/null)
SF_CUST_PHONE=$(echo "$SF_ORDERS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['orders'][-1]['customer_phone'])" 2>/dev/null)
[ "$SF_ORDER_ID" = "$ORDER_ID" ] && pass "Storefront sees order $ORDER_ID with phone $SF_CUST_PHONE" \
  || fail "Storefront order list" "expected $ORDER_ID, got $SF_ORDER_ID"

# 2e — storefront: confirmed → preparing
SF_U1=$(curl -s -b /tmp/hs_test_sf.txt -X PATCH "${BASE}/api/storefront/orders/${ORDER_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"preparing"}')
U1_STATUS=$(echo "$SF_U1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
[ "$U1_STATUS" = "preparing" ] && pass "Status: confirmed → preparing" \
  || fail "Status transition 1" "$SF_U1"

# 2f — storefront: preparing → ready
SF_U2=$(curl -s -b /tmp/hs_test_sf.txt -X PATCH "${BASE}/api/storefront/orders/${ORDER_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"ready"}')
U2_STATUS=$(echo "$SF_U2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
[ "$U2_STATUS" = "ready" ] && pass "Status: preparing → ready" \
  || fail "Status transition 2" "$SF_U2"

# 2g — customer sees ready status
sleep 1
CUST_ORDER2=$(curl -s -b /tmp/hs_test_cust.txt "${BASE}/api/customer/me/orders/${ORDER_ID}")
CUST_STATUS2=$(echo "$CUST_ORDER2" | python3 -c "import sys,json; print(json.load(sys.stdin)['order']['status'])" 2>/dev/null)
[ "$CUST_STATUS2" = "ready" ] && pass "Customer sees status: ready" \
  || fail "Customer status update" "expected ready, got $CUST_STATUS2"

# ---------- Scenario 3: Invalid transitions (fail-closed) ----------
echo ""
printf "${CYAN}═══ Scenario 3: Invalid transitions rejected ═══${NC}\n"

# 3a — try confirmed → ready (skip preparing)
HTTP_SKIP=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/hs_test_sf.txt \
  -X PATCH "${BASE}/api/storefront/orders/${ORDER_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed"}')
[ "$HTTP_SKIP" = "400" ] && pass "Cannot go back to 'confirmed' from 'ready' (400)" \
  || fail "Invalid transition not rejected" "got $HTTP_SKIP"

# 3b — try picked_up → preparing (should fail, picked_up is terminal)
# First, mark as picked_up
curl -s -b /tmp/hs_test_sf.txt -X PATCH "${BASE}/api/storefront/orders/${ORDER_ID}/status" \
  -H "Content-Type: application/json" -d '{"status":"picked_up"}' > /dev/null
HTTP_TERMINAL=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/hs_test_sf.txt \
  -X PATCH "${BASE}/api/storefront/orders/${ORDER_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"preparing"}')
[ "$HTTP_TERMINAL" = "400" ] && pass "Cannot change picked_up order (400)" \
  || fail "Terminal state not enforced" "got $HTTP_TERMINAL"

# ---------- Scenario 4: Customer cannot cancel their own order ----------
echo ""
printf "${CYAN}═══ Scenario 4: Customer CANNOT cancel ═══${NC}\n"

# Place a new order
ORDER2=$(curl -s -b /tmp/hs_test_cust.txt -X POST "${BASE}/api/orders" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"menu_item_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567899","name":"Test Dish","price_cents":999,"quantity":1}]}')
ORDER2_ID=$(echo "$ORDER2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('order_id',''))" 2>/dev/null)

# Try to PATCH status as customer
HTTP_NO_CANCEL=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/hs_test_cust.txt \
  -X PATCH "${BASE}/api/storefront/orders/${ORDER2_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"cancelled"}')
[ "$HTTP_NO_CANCEL" = "401" ] || [ "$HTTP_NO_CANCEL" = "403" ] \
  && pass "Customer cannot access storefront PATCH (${HTTP_NO_CANCEL})" \
  || fail "Customer should not be able to cancel" "got $HTTP_NO_CANCEL"

# ---------- Scenario 5: Storefront cancels order ----------
echo ""
printf "${CYAN}═══ Scenario 5: Storefront cancels order ═══${NC}\n"

# 5a — cancel from storefront
SF_CANCEL=$(curl -s -b /tmp/hs_test_sf.txt -X PATCH "${BASE}/api/storefront/orders/${ORDER2_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"cancelled","notes":"Customer called to cancel"}')
CANCEL_STATUS=$(echo "$SF_CANCEL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
[ "$CANCEL_STATUS" = "cancelled" ] && pass "Storefront cancelled order $ORDER2_ID" \
  || fail "Storefront cancel" "$SF_CANCEL"

# 5b — customer sees cancelled status
sleep 1
CUST_CANCEL=$(curl -s -b /tmp/hs_test_cust.txt "${BASE}/api/customer/me/orders/${ORDER2_ID}")
CANCEL_SEEN=$(echo "$CUST_CANCEL" | python3 -c "import sys,json; print(json.load(sys.stdin)['order']['status'])" 2>/dev/null)
[ "$CANCEL_SEEN" = "cancelled" ] && pass "Customer sees cancelled status" \
  || fail "Customer cancel visibility" "expected cancelled, got $CANCEL_SEEN"

# ---------- Scenario 6: Reservations ----------
echo ""
printf "${CYAN}═══ Scenario 6: Reservations ═══${NC}\n"

TODAY=$(date +%Y-%m-%d)
DOW=$(date +%u)  # 1=Monday, but our model uses 0=Sunday
# Convert to 0-6 (0=Monday) for our model
DOW_0=$(( (DOW + 6) % 7 ))

# 6a — admin creates a reservation slot
SLOT=$(curl -s -b /tmp/hs_test_admin.txt -X POST "${BASE}/api/admin/reservation-slots" \
  -H "Content-Type: application/json" \
  -d "{\"day_of_week\":${DOW_0},\"start_time\":\"14:00\",\"end_time\":\"15:00\",\"max_party_size\":6,\"max_reservations\":2}")
SLOT_ID=$(echo "$SLOT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
[ -n "$SLOT_ID" ] && pass "Reservation slot created for today (day $DOW_0, 14:00-15:00)" \
  || fail "Slot creation" "$SLOT"

# 6b — customer checks availability
AVAIL=$(curl -s "${BASE}/api/reservations/slots?reservation_date=${TODAY}&party_size=4")
SLOTS_AVAIL=$(echo "$AVAIL" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('slots',[])))" 2>/dev/null)
[ "$SLOTS_AVAIL" -ge 1 ] && pass "Customer sees $SLOTS_AVAIL available slot(s) for today" \
  || fail "Slot availability" "$AVAIL"

# 6c — customer books reservation
BOOK=$(curl -s -b /tmp/hs_test_cust.txt -X POST "${BASE}/api/reservations" \
  -H "Content-Type: application/json" \
  -d "{\"reservation_date\":\"${TODAY}\",\"start_time\":\"14:00:00\",\"party_size\":4}")
BOOK_ID=$(echo "$BOOK" | python3 -c "import sys,json; print(json.load(sys.stdin)['reservation']['id'])" 2>/dev/null)
[ -n "$BOOK_ID" ] && pass "Reservation booked: $BOOK_ID" \
  || fail "Reservation booking" "$BOOK"

# 6d — customer sees their reservation
MY_RES=$(curl -s -b /tmp/hs_test_cust.txt "${BASE}/api/customer/me/reservations")
HAS_RES=$(echo "$MY_RES" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('reservations',[])))" 2>/dev/null)
[ "$HAS_RES" -ge 1 ] && pass "Customer sees $HAS_RES reservation(s)" \
  || fail "Customer reservations" "$MY_RES"

# 6e — storefront sees today's reservations
SF_RES=$(curl -s -b /tmp/hs_test_sf.txt "${BASE}/api/storefront/reservations?reservation_date=${TODAY}")
SF_RES_COUNT=$(echo "$SF_RES" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('reservations',[])))" 2>/dev/null)
[ "$SF_RES_COUNT" -ge 1 ] && pass "Storefront sees $SF_RES_COUNT reservation(s) for today" \
  || fail "Storefront reservations" "$SF_RES"

# ---------- Scenario 7: PIN already used (can't re-pair) ----------
echo ""
printf "${CYAN}═══ Scenario 7: PIN reuse rejected ═══${NC}\n"

REUSE=$(curl -s -X POST "${BASE}/api/storefront/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"pin\":\"${DEVICE_PIN}\"}")
REUSE_MSG=$(echo "$REUSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail',''))" 2>/dev/null)
echo "$REUSE_MSG" | grep -qi "already" \
  && pass "Reused PIN rejected: '$REUSE_MSG'" \
  || fail "PIN reuse not rejected" "$REUSE"

# ---------- Results ----------
echo ""
echo "────────────────────────────────────────────"
printf "${GREEN}Passed: %d${NC}  ${RED}Failed: %d${NC}\n" "$PASS" "$FAIL"
echo "────────────────────────────────────────────"
[ "$FAIL" -eq 0 ] && printf "${GREEN}All integration tests passed.${NC}\n" && exit 0
printf "${RED}%d test(s) failed.${NC}\n" "$FAIL" && exit 1
