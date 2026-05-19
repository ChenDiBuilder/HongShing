import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 30000,
  use: {
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:3500",
      },
    },
    {
      name: "chromium-admin",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:3501",
      },
    },
  ],
  // Servers must be started manually:
  // Backend:   cd backend && APP_ENV=testing python -m uvicorn app.main:app --port 8500
  // Customer:  cd customer-web && npm run dev
  // Admin:     cd admin && npm run dev
});
