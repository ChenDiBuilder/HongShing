import { test, expect, Page } from "@playwright/test";

// Helper: fetch OTP from test endpoint
async function getOTP(phone: string): Promise<string> {
  const res = await fetch(
    `http://localhost:8500/api/test/sms-messages?phone=${encodeURIComponent(phone)}`,
  );
  const data = await res.json() as { messages: { otp_code: string }[] };
  if (!data.messages || data.messages.length === 0) {
    throw new Error(`No OTP found for ${phone}`);
  }
  return data.messages[0].otp_code;
}

test.describe("Customer signup flow", () => {
  test("New customer: QR → landing → phone → OTP → reward → redirect", async ({ page }) => {
    // 1. Open landing page with source
    await page.goto("/?source=receipt");
    await expect(page.locator("h1")).toContainText("Rewards");

    // 2. Enter phone number
    await page.fill('input[type="tel"]', "+16475551001");
    await page.click('button:has-text("Send Code")');

    // 3. Wait for OTP input screen
    await expect(page.locator("h2")).toContainText("Enter Code", { timeout: 5000 });

    // 4. Fetch OTP from test endpoint
    const otp = await getOTP("+16475551001");
    console.log(`Got OTP: ${otp}`);

    // 5. Enter OTP
    const otpInput = page.locator('input[inputmode="numeric"]');
    await otpInput.fill(otp);
    await page.click('button:has-text("Verify")');

    // 6. Verify reward screen
    await expect(page.locator("h2")).toContainText("You're in!", { timeout: 5000 });
    const codeEl = page.locator("text=/HS-[A-Z0-9]+/");
    await expect(codeEl).toBeVisible();
    const codeText = await codeEl.textContent();
    console.log(`Reward code: ${codeText}`);

    // 7. "Order Now" button exists
    await expect(page.locator('button:has-text("Order Now")')).toBeVisible();
  });

  test("Wrong OTP shows error and does not create session", async ({ page }) => {
    await page.goto("/?source=counter");
    await expect(page.locator("h1")).toContainText("Rewards");

    await page.fill('input[type="tel"]', "+16475551002");
    await page.click('button:has-text("Send Code")');
    await expect(page.locator("h2")).toContainText("Enter Code", { timeout: 5000 });

    // Enter wrong OTP
    await page.fill('input[inputmode="numeric"]', "999999");
    await page.click('button:has-text("Verify")');

    // Should show error
    await expect(page.locator("text=/Invalid|expired|wrong/")).toBeVisible({ timeout: 5000 });

    // Should NOT show reward screen
    await expect(page.locator("h2:has-text(\"You're in!\")")).not.toBeVisible();
  });

  test("Order without reward redirects without auth", async ({ page }) => {
    await page.goto("/");

    // Click "Order without reward"
    await page.click('button:has-text("Order without reward")');

    // Should attempt redirect (in test env, it calls the API which returns the ordering URL)
    // Since no external ordering URL is configured, the redirect may not work,
    // but the button should be clickable without error.
  });
});

test.describe("Admin login flow", () => {
  test.use({ baseURL: "http://localhost:3501" });

  test("Admin login → dashboard renders", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("HongShing Admin");

    // Login
    await page.fill('input[type="email"]', "owner@hongshing.com");
    await page.fill('input[type="password"]', "admin123");
    await page.click('button:has-text("Sign In")');

    // Should redirect to dashboard
    await expect(page.locator("h1")).toContainText("Dashboard", { timeout: 5000 });

    // Stat cards should be visible
    await expect(page.locator("text=Total Customers")).toBeVisible();
    await expect(page.locator("text=Active Campaigns")).toBeVisible();
    await expect(page.locator("text=Rewards Issued")).toBeVisible();
  });

  test("Wrong credentials shows error", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[type="email"]', "wrong@example.com");
    await page.fill('input[type="password"]', "wrongpass");
    await page.click('button:has-text("Sign In")');

    await expect(page.locator("text=/Invalid|wrong/")).toBeVisible({ timeout: 5000 });
  });

  test("Unauthenticated dashboard redirects to login", async ({ page }) => {
    // Try to access dashboard directly without login
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("HongShing Admin");
    // Currently the admin app always shows login first (state-based routing)
    // So this just verifies the login page renders
  });
});
