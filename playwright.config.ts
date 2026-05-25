import { defineConfig, devices } from "@playwright/test";

const CF = "https://d1qkx0vmdo9wnw.cloudfront.net";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 90000,
  use: {
    trace: "on-first-retry",
    baseURL: CF,
  },
  projects: [
    {
      name: "production",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
