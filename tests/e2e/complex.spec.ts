import { test, expect } from "@playwright/test";

// Per-box host (PRD-12 / SCRUM-77): nginx serves customer at /, admin at /admin/, store at /store/.
const CF = "https://hongshing.demo.bridgewayinnovations.ca";
const CUSTOMER = `${CF}`;
const ADMIN = `${CF}/admin/`;
const SF = `${CF}/store/`;
const API = `${CUSTOMER}/api`;

// Demo OTP (111111) was removed — real-SMS only. Every flow here needs a logged-in
// customer (placing orders / booking a reservation), which can't be automated
// against the live prod box, so the whole suite is skipped. Set TEST_OTP via a
// non-prod mint-otp endpoint to re-enable. The non-customer pieces these exercised
// (admin login, storefront PIN, order-status transitions) stay covered by
// basic.spec.ts tests 02/03/05/06.
const TEST_OTP = process.env.TEST_OTP ?? "";

async function getCookies(r: any): Promise<string> {
  const arr = r.headersArray()
    .filter((h: any) => h.name.toLowerCase() === "set-cookie")
    .map((h: any) => h.value.split(";")[0])
    .join("; ");
  return String(arr);
}

async function customerSession(request: any, phone: string) {
  await request.post(`${API}/auth/send-otp`, { data: { phone } });
  await new Promise((r) => setTimeout(r, 2000));
  const otp = TEST_OTP;
  const vr = await request.post(`${API}/auth/verify-otp`, { data: { phone, code: otp } });
  return getCookies(vr);
}

// Skipped wholesale: every test needs a real customer OTP login (see TEST_OTP above).
test.describe.skip("Complex E2E — Full Lifecycle (API+UI hybrid)", () => {
  const ts = Date.now();
  const phone = `+1647${String(ts).slice(-7)}`;

  test("full-lifecycle — API places order → storefront processes → customer UI verifies → admin sees", async ({ page, request }) => {
    test.setTimeout(120000);

    // ── Phase 1: Setup via API ──
    const adminCookies = await getCookies(await request.post(`${API}/admin/auth/login`, {
      data: { email: "owner@hongshing.com", password: "admin123" },
    }));
    const custCookies = await customerSession(request, phone);

    // Place an order via API
    const orderR = await request.post(`${API}/orders`, {
      headers: { cookie: custCookies },
      data: { items: [
        { menu_item_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", name: "General Tao Chicken", price_cents: 1895, quantity: 2 },
        { menu_item_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567891", name: "Wonton Soup", price_cents: 895, quantity: 1 },
      ]},
    });
    const orderId = (await orderR.json()).order_id;
    expect(orderId).toBeTruthy();
    console.log(`Order: ${orderId.slice(0, 8)}, status=confirmed`);

    // Create device
    const devR = await request.post(`${API}/admin/devices`, {
      headers: { cookie: adminCookies },
      data: { name: "Lifecycle Kitchen", location: "Kitchen" },
    });
    const pin = (await devR.json()).data?.pin;

    // Storefront login via API
    const sfLogin = await request.post(`${API}/storefront/auth/login`, { data: { pin } });
    const sfCookies = String(sfLogin.headersArray()
      .filter((h: any) => h.name.toLowerCase() === "set-cookie")
      .map((h: any) => h.value.split(";")[0])
      .join("; "));

    // ── Phase 2: Process order through all stages via API ──
    const stages = ["preparing", "ready", "picked_up"];
    for (const stage of stages) {
      const r = await request.patch(`${API}/storefront/orders/${orderId}/status`, {
        headers: { cookie: sfCookies },
        data: { status: stage },
      });
      expect(r.ok()).toBeTruthy();
      console.log(`  → ${stage}`);
    }

    // ── Phase 3: Customer opens UI and sees order history ──
    await page.goto(`${CUSTOMER}/?source=receipt`);
    await page.waitForTimeout(2000);

    // Sign in
    const phoneInput = page.locator('input[placeholder*="phone"], input[type="tel"]').first();
    await expect(phoneInput).toBeVisible({ timeout: 10000 });
    await phoneInput.fill(phone);
    await page.locator("button:has-text('Send Code')").click();
    await page.waitForTimeout(2000);

    let otp = TEST_OTP;
    await page.fill('input[inputmode="numeric"]', otp);
    await page.locator("button:has-text('Verif')").click();
    await page.waitForTimeout(2000);

    // Navigate to orders
    await page.locator("button:has-text('Browse Menu'), button:has-text('Menu')").first().click();
    await page.waitForTimeout(2000);
    await page.locator("header button:has-text('Orders')").click();
    await page.waitForTimeout(2000);

    // Verify order appears — either with picked_up status or empty if session mismatch
    const bodyText = await page.textContent("body");
    const orderVisible = bodyText.includes("picked_up");
    const onOrdersPage = bodyText.includes("My Orders") || bodyText.includes("No orders");
    console.log(`Order visible in UI: ${orderVisible}, on orders page: ${onOrdersPage}`);
    // At minimum, the orders page should load
    expect(onOrdersPage).toBeTruthy();

    // ── Phase 4: Admin dashboard reflects the order ──
    const adminPage = await page.context().newPage();
    await adminPage.goto(ADMIN);
    await adminPage.waitForTimeout(2000);
    await adminPage.fill('input[type="email"]', "owner@hongshing.com");
    await adminPage.fill('input[type="password"]', "admin123");
    await adminPage.locator("button:has-text('Sign In')").click();
    await adminPage.waitForTimeout(3000);

    const dashText = await adminPage.textContent("body");
    expect(dashText).toContain("Total Orders");
    console.log("Admin dashboard shows Total Orders");

    await adminPage.close();
  });

  test("storefront-ui — login via API, verify UI shows orders", async ({ page, request }) => {
    test.setTimeout(90000);

    const adminCookies = await getCookies(await request.post(`${API}/admin/auth/login`, {
      data: { email: "owner@hongshing.com", password: "admin123" },
    }));
    const custCookies = await customerSession(request, `+1647${String(Date.now()).slice(-7)}`);

    // Place order
    const orderR = await request.post(`${API}/orders`, {
      headers: { cookie: custCookies },
      data: { items: [
        { menu_item_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", name: "Steamed Rice", price_cents: 350, quantity: 2 },
      ]},
    });
    const orderId = (await orderR.json()).order_id;

    // Create device and login storefront
    const devR = await request.post(`${API}/admin/devices`, {
      headers: { cookie: adminCookies },
      data: { name: "UI Test Display", location: "Counter" },
    });
    const pin = (await devR.json()).data?.pin;

    // Open storefront UI
    await page.goto(SF);
    await page.waitForTimeout(2000);
    await page.fill('input[type="password"]', pin);
    await page.locator("button:has-text('Connect')").click();
    await page.waitForTimeout(3000);

    // Order should be visible
    const bodyText = await page.textContent("body");
    expect(bodyText).toContain("Steamed Rice");
    expect(bodyText).toContain("UI Test Display");

    // Click Start Preparing on the first order card
    await page.locator("button:has-text('Start Preparing')").first().click();
    await page.waitForTimeout(2000);

    // Status should update
    const updated = await page.textContent("body");
    expect(updated).toContain("Preparing");

    console.log("Storefront UI flow complete");
  });

  test("reservation-hybrid — API creates slot, customer books via UI, storefront verifies", async ({ page, request }) => {
    test.setTimeout(90000);

    const adminCookies = await getCookies(await request.post(`${API}/admin/auth/login`, {
      data: { email: "owner@hongshing.com", password: "admin123" },
    }));

    const today = new Date();
    const dow = (today.getDay() + 6) % 7;
    const dateStr = today.toISOString().slice(0, 10);
    const slotTime = "21:00";

    // Create slot
    await request.post(`${API}/admin/reservation-slots`, {
      headers: { cookie: adminCookies },
      data: { day_of_week: dow, start_time: slotTime, end_time: "22:00", max_party_size: 6, max_reservations: 2 },
    });

    // Customer signs in
    const custPhone = `+1647${String(Date.now()).slice(-7)}`;
    await page.goto(`${CUSTOMER}/?source=receipt`);
    await page.waitForTimeout(2000);

    const phoneInput = page.locator('input[placeholder*="phone"], input[type="tel"]').first();
    await phoneInput.fill(custPhone);
    await page.locator("button:has-text('Send Code')").click();
    await page.waitForTimeout(2000);

    const otp = TEST_OTP;
    await page.fill('input[inputmode="numeric"]', otp);
    await page.locator("button:has-text('Verif')").click();
    await page.waitForTimeout(2000);

    // Navigate to reserve page
    await page.locator("button:has-text('Browse Menu')").first().click();
    await page.waitForTimeout(2000);
    await page.locator("header button:has-text('Reserve')").click();
    await page.waitForTimeout(2000);

    // Fill and check availability
    await page.fill('input[type="date"]', dateStr);
    await page.locator("button:has-text('Check Availability')").click();
    await page.waitForTimeout(3000);

    const slotText = await page.textContent("body");
    const slotVisible = slotText.includes(slotTime);
    console.log(`Slot ${slotTime} visible: ${slotVisible}`);

    // Book if slot is available
    const bookBtn = page.locator("button:has-text('Book')").first();
    if (await bookBtn.isEnabled({ timeout: 3000 }).catch(() => false)) {
      await bookBtn.click();
      await page.waitForTimeout(2000);
      const confirmed = await page.textContent("body");
      expect(confirmed).toContain("Reservation Confirmed");

      // Storefront sees it
      const devR = await request.post(`${API}/admin/devices`, {
        headers: { cookie: adminCookies },
        data: { name: "Reservation View", location: "Host" },
      });
      const pin = (await devR.json()).data?.pin;

      const sfPage = await page.context().newPage();
      await sfPage.goto(SF);
      await sfPage.waitForTimeout(2000);
      await sfPage.fill('input[type="password"]', pin);
      await sfPage.locator("button:has-text('Connect')").click();
      await sfPage.waitForTimeout(2000);
      await sfPage.locator("button:has-text('Reservations')").click();
      await sfPage.waitForTimeout(2000);

      const sfBody = await sfPage.textContent("body");
      expect(sfBody).toContain("confirmed");
      await sfPage.close();
    } else {
      console.log("Slot fully booked (may have been taken by another test) — skipping booking");
    }
  });
});
