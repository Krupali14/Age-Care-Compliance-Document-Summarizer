import { expect, test } from "@playwright/test";
import path from "node:path";
import { FIXTURES, SAMPLES, signUp, uniqueEmail, uploadAndWait } from "./helpers";

const POLICY = path.join(SAMPLES, "Sunrise-Grove-Incident-Management-Policy.pdf");

test.describe("documents", () => {
  test("upload, extract, and read every category", async ({ page }) => {
    await signUp(page, uniqueEmail("upload"));
    const card = await uploadAndWait(page, POLICY);
    await expect(card).toHaveAttribute("aria-label", /— Ready$/);

    await card.click();
    await expect(page).toHaveURL(/\/dashboard\/documents\/\d+$/);

    // Regression: the detail page never re-fetched, so a document opened while it
    // was still processing stayed on "still being processed" with every tab at 0
    // until the user reloaded.
    await expect(page.getByRole("status")).toHaveCount(0);

    // Regression: batching made the model omit the optional finding lists, so an
    // obligation-dense document came back with a summary and nothing else.
    const obligations = page.getByRole("tab", { name: /^Obligations/ });
    await expect(obligations).not.toHaveAccessibleName(/, 0 items/);

    await expect(page.getByRole("tabpanel")).not.toBeEmpty();
    for (const name of ["Obligations", "Risks", "Deadlines", "Actions", "Sections"]) {
      await page.getByRole("tab", { name: new RegExp(`^${name}`) }).click();
      await expect(page.getByRole("tab", { name: new RegExp(`^${name}`) })).toHaveAttribute("aria-selected", "true");
      await expect(page.getByRole("tabpanel")).toBeVisible();
    }
  });

  test("a document that is not compliance material is refused with a reason", async ({ page }) => {
    await signUp(page, uniqueEmail("scope"));
    const card = await uploadAndWait(page, path.join(FIXTURES, "office-supplies-invoice.pdf"));
    await expect(card).toHaveAttribute("aria-label", /— Not supported$/);

    await card.click();
    await expect(page.getByText(/can.t be summarised/)).toBeVisible();
    // Nothing to read and nothing to ask about, so neither is offered.
    await expect(page.getByRole("tablist")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Ask AI" })).toHaveCount(0);
  });

  test("a file that is not really a PDF is rejected with an actionable message", async ({ page }) => {
    await signUp(page, uniqueEmail("badfile"));
    const chooser = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Upload document" }).click();
    (await chooser).setFiles(path.join(FIXTURES, "not-really-a-pdf.pdf"));

    // Regression: upload failures were rendered but never announced.
    await expect(page.getByRole("status")).toContainText(/not a readable PDF/);
    await expect(page.locator("[role=link]")).toHaveCount(0);
  });

  test("a document can be deleted, with confirmation", async ({ page }) => {
    await signUp(page, uniqueEmail("delete"));
    const card = await uploadAndWait(page, POLICY);

    await page.getByRole("button", { name: /^Delete / }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("This can't be undone");

    // Escape must cancel, not delete.
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(card).toBeVisible();

    await page.getByRole("button", { name: /^Delete / }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
    await expect(card).toHaveCount(0);
    await expect(page.getByText("No documents yet")).toBeVisible();
  });

  test("one account cannot open another's document", async ({ page }) => {
    await signUp(page, uniqueEmail("owner"));
    const card = await uploadAndWait(page, POLICY);
    await card.click();
    const url = page.url();

    await page.getByRole("button", { name: /Account menu/ }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await signUp(page, uniqueEmail("intruder"));

    await page.goto(url);
    await expect(page.getByText("Document not found")).toBeVisible();
  });

  test("an unknown route renders the not-found page", async ({ page }) => {
    await signUp(page, uniqueEmail("404"));
    await page.goto("/dashboard/nope");
    await expect(page.getByText("Page not found")).toBeVisible();
  });
});
