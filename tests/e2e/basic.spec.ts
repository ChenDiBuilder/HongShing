import { test, expect } from "@playwright/test";

const CF = "https://d1qkx0vmdo9wnw.cloudfront.net";
const CUSTOMER = `${CF}/product-demo/hongshing`;
const ADMIN = `${CF}/product-demo/hongshing-admin/`;
const SF = `${CF}/product-demo/hongshing-storefront/`;
const API = `${CUSTOMER}/api`;

const ts = Date.now();
const testPhone = `+1647${String(ts).slice(-7)}`;
const shortPhone = testPhone.slice(2);

test.describe("HongShing Production E2E", () => {

  test("01 — Customer: send OTP and verify", async ({ page, request }) => {
    test.setTimeout(90000);
    await page.goto(`${CUSTOMER}/?source=receipt`);
    await page.waitForTimeout(3000);

    // Landing page: find phone input and Send Code button
    const phoneInput = page.locator('input[placeholder*="phone"], input[type="tel"]').first();
    await expect(phoneInput).toBeVisible({ timeout: 10000 });
    await phoneInput.fill(testPhone);
    await page.locator("button:has-text('Send Code')").click();
    await page.waitForTimeout(2000);

    const otp = "111111";

    // Enter OTP on the OTP page
    const codeInput = page.locator('input[inputmode="numeric"]').first();
    await expect(codeInput).toBeVisible({ timeout: 5000 });
    await codeInput.fill(otp);
    await page.locator("button:has-text('Verif')").click();
    await page.waitForTimeout(3000);

    // Should see reward page with Browse Menu button
    await expect(page.locator("button:has-text('Browse Menu'), button:has-text('Menu')").first()).toBeVisible({ timeout: 10000 });
  });

  test("02 — Admin: login, see dashboard", async ({ page }) => {
    test.setTimeout(60000);
    await page.goto(ADMIN);
    await page.waitForTimeout(2000);

    await page.fill('input[type="email"]', "owner@hongshing.com");
    await page.fill('input[type="password"]', "admin123");
    await page.locator("button:has-text('Sign In')").click();
    await page.waitForTimeout(3000);

    // Verify dashboard loaded via heading
    await expect(page.locator("h1:has-text('Dashboard')")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Total Customers")).toBeVisible();
    await expect(page.locator("text=Total Orders")).toBeVisible();
  });

  test("03 — Storefront: login with PIN and see orders tab", async ({ page, request }) => {
    test.setTimeout(60000);

    const loginRes = await request.post(`${API}/admin/auth/login`, {
      data: { email: "owner@hongshing.com", password: "admin123" },
    });
    const cookies = loginRes.headersArray()
      .filter((h) => h.name.toLowerCase() === "set-cookie")
      .map((h) => h.value.split(";")[0])
      .join("; ");

    const createRes = await request.post(`${API}/admin/devices`, {
      headers: { cookie: cookies },
      data: { name: "E2E Storefront", location: "Counter" },
    });
    const newDevice = (await createRes.json()).data;
    const pin = newDevice?.pin;
    if (!pin) { test.skip(true, "Could not create device"); return; }
    console.log(`Device PIN: ${pin}`);

    await page.goto(SF);
    await page.waitForTimeout(2000);

    await page.fill('input[type="password"]', pin);
    await page.locator("button:has-text('Connect')").click();
    await page.waitForTimeout(3000);

    // Device name in header
    await expect(page.locator("text=E2E Storefront")).toBeVisible({ timeout: 10000 });

    // Tabs should be visible
    await expect(page.locator("button:has-text('Orders')")).toBeVisible();
    await expect(page.locator("button:has-text('Reservations')")).toBeVisible();

    // Switch to reservations
    await page.locator("button:has-text('Reservations')").click();
    await page.waitForTimeout(1000);
    await expect(page.locator("text=Today's Reservations")).toBeVisible({ timeout: 5000 });
  });

  test("04 — Customer: returning sign-in and view orders", async ({ page, request }) => {
    test.setTimeout(90000);
    await page.goto(`${CUSTOMER}/?source=receipt`);
    await page.waitForTimeout(3000);

    // Re-sign in with same phone
    const phoneInput = page.locator('input[placeholder*="phone"], input[type="tel"]').first();
    await expect(phoneInput).toBeVisible({ timeout: 10000 });
    await phoneInput.fill(testPhone);
    await page.locator("button:has-text('Send Code')").click();
    await page.waitForTimeout(2000);

    const otp = "111111";

    const codeInput = page.locator('input[inputmode="numeric"]').first();
    await expect(codeInput).toBeVisible({ timeout: 5000 });
    await codeInput.fill(otp);
    await page.locator("button:has-text('Verif')").click();
    await page.waitForTimeout(3000);

    // On reward page, click Browse Menu to get to menu page with header
    await expect(page.locator("button:has-text('Browse Menu'), button:has-text('Menu')").first()).toBeVisible({ timeout: 10000 });
    await page.locator("button:has-text('Browse Menu'), button:has-text('Menu')").first().click();
    await page.waitForTimeout(3000);

    // Header should show Orders, Rewards, Reserve for signed-in users
    await expect(page.locator("header button:has-text('Orders')")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("header button:has-text('Rewards')")).toBeVisible({ timeout: 5000 });
  });

  test("05 — Storefront: PIN reuse is rejected", async ({ page, request }) => {
    test.setTimeout(60000);

    const loginRes = await request.post(`${API}/admin/auth/login`, {
      data: { email: "owner@hongshing.com", password: "admin123" },
    });
    const cookies = loginRes.headersArray()
      .filter((h) => h.name.toLowerCase() === "set-cookie")
      .map((h) => h.value.split(";")[0])
      .join("; ");

    // Create a device to get a valid PIN, then try to reuse it
    const createRes = await request.post(`${API}/admin/devices`, {
      headers: { cookie: cookies },
      data: { name: "E2E Reuse Test", location: "Test" },
    });
    const pin = (await createRes.json()).data?.pin;
    if (!pin) { test.skip(true); return; }

    // First login — succeeds
    await page.goto(SF);
    await page.waitForTimeout(2000);
    await page.fill('input[type="password"]', pin);
    await page.locator("button:has-text('Connect')").click();
    await page.waitForTimeout(2000);

    // Second login attempt with same PIN — should fail
    const page2 = await page.context().newPage();
    await page2.goto(SF);
    await page2.waitForTimeout(2000);
    await page2.fill('input[type="password"]', pin);
    await page2.locator("button:has-text('Connect')").click();
    await page2.waitForTimeout(3000);

    const bodyText = await page2.textContent("body");
    expect(bodyText).toContain("already");
    await page2.close();
  });

  test("06 — Admin: create reservation slot", async ({ page }) => {
    test.setTimeout(60000);
    await page.goto(ADMIN);
    await page.waitForTimeout(2000);

    await page.fill('input[type="email"]', "owner@hongshing.com");
    await page.fill('input[type="password"]', "admin123");
    await page.locator("button:has-text('Sign In')").click();
    await page.waitForTimeout(3000);

    // Navigate to Reservation Slots
    await page.locator("button:has-text('Reservation Slots')").click();
    await page.waitForTimeout(1000);

    // Fill form
    await page.selectOption("select", { index: 1 });
    const timeInputs = page.locator('input[type="time"]');
    await timeInputs.nth(0).fill("15:00");
    await timeInputs.nth(1).fill("16:00");

    const numInput = page.locator('input[type="number"]').first();
    if (await numInput.isVisible()) {
      await numInput.fill("6");
    }

    await page.locator("button:has-text('Add Slot')").click();
    await page.waitForTimeout(2000);

    await expect(page.locator("text=15:00").first()).toBeVisible({ timeout: 5000 });
  });
});
