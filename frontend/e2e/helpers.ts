import { expect, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const SAMPLES = path.resolve(here, "../../samples");
export const FIXTURES = path.resolve(here, "fixtures");

/** A fresh address per run, so a spec never collides with a previous one's data. */
export function uniqueEmail(tag: string): string {
  return `e2e-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

export const PASSWORD = "secret123";

/** Register through the UI and land on the dashboard. */
export async function signUp(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByRole("button", { name: /Need an account\? Register/ }).click();
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

export async function signIn(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.locator("button[type=submit]").click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

/** Upload a document. Returns its card as soon as the card exists.
 *
 *  Use this when the test is about the interface rather than the extraction —
 *  most of them are. Waiting for "Ready" when the test does not need it makes
 *  every such test depend on a real model call behind a shared rate limiter, which
 *  is how the keyboard-journey test came to fail on a busy machine while passing in
 *  19 seconds on an idle one. */
export async function upload(page: Page, filePath: string) {
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Upload document" }).click();
  (await chooser).setFiles(filePath);

  const card = page.locator(`[role=link][aria-label^="${path.basename(filePath)}"]`);
  await expect(card).toBeVisible();
  return card;
}

/** Upload a document and wait for extraction to finish. Returns its card.
 *
 *  Only for tests that genuinely assert on extracted content. */
export async function uploadAndWait(page: Page, filePath: string) {
  const card = await upload(page, filePath);
  const name = path.basename(filePath);
  // "Reading" → "Ready" is driven by polling, not by a reload.
  await expect(card).toHaveAttribute("aria-label", new RegExp(`${escapeRe(name)} — (Ready|Not supported|Failed)$`), {
    timeout: 170_000,
  });
  return card;
}

/** Open a document and wait for the assistant panel, which appears as soon as the
 *  document has sections — before extraction finishes. */
export async function openDocument(page: Page, card: ReturnType<Page["locator"]>) {
  await card.click();
  await expect(page).toHaveURL(/\/dashboard\/documents\/\d+$/);
  await expect(page.getByRole("log")).toBeVisible({ timeout: 60_000 });
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Plant a syntactically valid JWT whose expiry has already passed. */
export async function plantExpiredToken(page: Page): Promise<void> {
  await page.evaluate(() => {
    const b64 = (o: object) =>
      btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const header = b64({ alg: "HS256", typ: "JWT" });
    const payload = b64({ sub: "1", email: "x@y.com", exp: Math.floor(Date.now() / 1000) - 60 });
    localStorage.setItem("token", `${header}.${payload}.sig`);
  });
}
