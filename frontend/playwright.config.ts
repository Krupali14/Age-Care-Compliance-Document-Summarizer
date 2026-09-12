import { defineConfig, devices } from "@playwright/test";

/**
 * Regression suite for the running application.
 *
 * These drive the real stack — Vite on 3002, FastAPI on 8002, Postgres — because
 * every bug this suite covers was invisible to a unit test: a panel that never
 * scrolled, a control with no keyboard path, a page that never re-fetched.
 *
 * Start the stack first (`make up`, or `docker compose up -d`), then `npm run e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  // Each spec signs in as its own account and uploads its own documents, so they
  // do not share state — but the API rate-limits registrations per address, and
  // parallel workers all arrive from one address.
  workers: 1,
  fullyParallel: false,
  // A document upload runs a real extraction: parse, relevance gate, then batched
  // model calls. Generous, and still a genuine failure if it is exceeded.
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3002",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
      // The phone specs assert the bottom-sheet assistant, which only exists below
      // the lg breakpoint — at desktop width there is no "Ask AI" button to click.
      testIgnore: /mobile\.spec\.ts/,
    },
    // Pixel 5 rather than an iPhone profile: it is Chromium, so the suite needs one
    // browser download instead of two, and these specs test responsive layout and
    // touch behaviour rather than engine differences.
    { name: "mobile", use: { ...devices["Pixel 5"] }, testMatch: /mobile\.spec\.ts/ },
  ],
});
