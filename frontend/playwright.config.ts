import { defineConfig, devices } from "@playwright/test";

/**
 * E2E runs against the production build plus a deterministic backend.
 * Build first with the E2E API base baked in:
 *   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 npm run build
 * then: npm run test:e2e
 */
const API_PORT = 8001;
const WEB_PORT = 3000;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: "mobile-links.spec.ts",
    },
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 800 } },
      testMatch: "mobile-links.spec.ts",
    },
  ],
  webServer: [
    {
      // Deterministic backend: saved fixtures only, test provider gated by env.
      // No GitHub calls, no live AI provider calls.
      command: `uv run uvicorn api.main:app --app-dir src --port ${API_PORT}`,
      cwd: "..",
      port: API_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        PUBLIC_DATA_FIXTURE_ONLY: "1",
        E2E_TEST_MODE: "1",
        AI_REVIEW_PROVIDER: "",
        AI_REVIEW_BASE_URL: "",
        AI_REVIEW_MODEL: "",
        AI_REVIEW_API_KEY: "",
        GITHUB_TOKEN: "",
      },
    },
    {
      command: `npm run start -- --port ${WEB_PORT}`,
      port: WEB_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
});
