import { expect, test } from "@playwright/test";
import { PASSWORD, plantExpiredToken, signIn, signUp, uniqueEmail } from "./helpers";

test.describe("authentication", () => {
  test("a new account can register, sign out and sign back in", async ({ page }) => {
    const email = uniqueEmail("auth");
    await signUp(page, email);

    // Regression: the avatar was a hardcoded "A" and the signed-in address
    // appeared nowhere in the application.
    const avatar = page.getByRole("button", { name: `Account menu for ${email}` });
    await expect(avatar).toHaveText(email[0].toUpperCase());

    await avatar.click();
    await expect(page.getByRole("menu")).toContainText(email);
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await signIn(page, email);
  });

  test("a signed-in user is redirected away from the sign-in form", async ({ page }) => {
    // Regression: /login offered to authenticate a user whose session was live.
    await signUp(page, uniqueEmail("redirect"));
    await page.goto("/login");
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("a short password is refused before the request is sent", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /Need an account\? Register/ }).click();
    await page.locator("#email").fill(uniqueEmail("short"));
    await page.locator("#password").fill("short");
    await page.locator("button[type=submit]").click();

    await expect(page).toHaveURL(/\/login$/);
    expect(await page.locator("#password").evaluate((el: HTMLInputElement) => el.validationMessage))
      .toContain("8 characters");
  });

  test("a duplicate address reports the real reason", async ({ page }) => {
    const email = uniqueEmail("dupe");
    await signUp(page, email);
    await page.getByRole("button", { name: /Account menu/ }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();

    await page.goto("/login");
    await page.getByRole("button", { name: /Need an account\? Register/ }).click();
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(PASSWORD);
    await page.locator("button[type=submit]").click();

    await expect(page.getByRole("alert")).toHaveText("Email already registered");
  });

  test("switching between sign-in and register clears a stale error", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#email").fill(uniqueEmail("stale"));
    await page.locator("#password").fill("wrongpassword");
    await page.locator("button[type=submit]").click();
    await expect(page.getByRole("alert")).toBeVisible();

    await page.getByRole("button", { name: /Need an account\? Register/ }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("an expired session says so instead of silently bouncing", async ({ page }) => {
    // Regression: the user was returned to a sign-in form with no explanation,
    // which reads as the application having lost their work.
    await signUp(page, uniqueEmail("expiry"));
    await plantExpiredToken(page);
    await page.goto("/dashboard");

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("status")).toContainText("session expired");

    // …and the notice does not follow them around afterwards.
    await page.goto("/login");
    await expect(page.getByRole("status")).toHaveCount(0);
  });

  test("a protected route is unreachable without a session", async ({ page }) => {
    await page.goto("/dashboard/documents/1");
    await expect(page).toHaveURL(/\/login$/);
  });
});
