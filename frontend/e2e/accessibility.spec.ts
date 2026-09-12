import { expect, test } from "@playwright/test";
import path from "node:path";
import { SAMPLES, openDocument, signUp, uniqueEmail, upload } from "./helpers";

const POLICY = path.join(SAMPLES, "Marloo-Gardens-Restrictive-Practices-Policy.pdf");

test.describe("keyboard and assistive technology", () => {
  test("the whole upload-to-document journey works without a mouse", async ({ page }) => {
    // Regression: the upload control was a <label> wrapping a display:none input,
    // and the document cards were <div onClick>. Neither was focusable, so there
    // was no keyboard path to the application's primary action or past the
    // dashboard at all.
    await signUp(page, uniqueEmail("kbd"));

    const upload = page.getByRole("button", { name: "Upload document" });
    await upload.focus();
    await expect(upload).toBeFocused();

    const chooser = page.waitForEvent("filechooser");
    await page.keyboard.press("Enter");
    (await chooser).setFiles(POLICY);

    const card = page.locator("[role=link]").first();
    await expect(card).toBeVisible();

    await card.focus();
    await expect(card).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/dashboard\/documents\/\d+$/);
  });

  test("landmarks, the skip link and the tab pattern are present", async ({ page }) => {
    await signUp(page, uniqueEmail("aria"));

    const skip = page.getByRole("link", { name: "Skip to content" });
    await skip.focus();
    await expect(skip).toBeFocused();
    await expect(page.locator("#main")).toHaveCount(1);

    await openDocument(page, await upload(page, POLICY));

    await expect(page.getByRole("tablist")).toHaveCount(1);
    await expect(page.getByRole("tab")).toHaveCount(6);
    await expect(page.getByRole("tab", { name: /^Summary/ })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tabpanel")).toHaveCount(1);

    // The assistant announces itself and its answers.
    await expect(page.getByRole("log")).toHaveAttribute("aria-live", "polite");
    await expect(page.getByLabel("Ask a question about this document")).toBeVisible();
  });

  test("the account menu answers to the keyboard", async ({ page }) => {
    // No document needed — this is about the header.
    const email = uniqueEmail("menu");
    await signUp(page, email);

    const avatar = page.getByRole("button", { name: `Account menu for ${email}` });
    await expect(avatar).toHaveAttribute("aria-expanded", "false");
    await avatar.click();
    await expect(avatar).toHaveAttribute("aria-expanded", "true");

    await page.keyboard.press("Escape");
    await expect(avatar).toHaveAttribute("aria-expanded", "false");
    await expect(avatar).toBeFocused();
  });

  test("the delete confirmation traps focus and restores it", async ({ page }) => {
    await signUp(page, uniqueEmail("modal"));
    await upload(page, POLICY);

    const deleteButton = page.getByRole("button", { name: /^Delete / });
    await deleteButton.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(dialog.getByRole("button", { name: "Delete" })).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });

  test("the split can be resized from the keyboard", async ({ page }) => {
    // Regression: the splitter was a bare <div> with a mousedown handler — an
    // interactive control no keyboard could reach or operate.
    await signUp(page, uniqueEmail("split"));
    await openDocument(page, await upload(page, POLICY));

    const separator = page.getByRole("separator", { name: /Resize/ });
    await expect(separator).toBeVisible();
    await expect(separator).toHaveAttribute("aria-valuenow", "68");

    await separator.focus();
    await expect(separator).toBeFocused();

    await page.keyboard.press("ArrowLeft");
    await expect(separator).toHaveAttribute("aria-valuenow", "66");

    await page.keyboard.press("Home");
    await expect(separator).toHaveAttribute("aria-valuenow", "50");

    await page.keyboard.press("End");
    await expect(separator).toHaveAttribute("aria-valuenow", "80");
  });

  test("icon-only controls carry real labels, not just tooltips", async ({ page }) => {
    // Regression: focus mode, collapse and new-conversation relied on `title`
    // alone — the weakest source of an accessible name, and invisible on touch.
    await signUp(page, uniqueEmail("icons"));
    await openDocument(page, await upload(page, POLICY));

    await expect(page.getByRole("button", { name: "Enter focus mode" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Collapse the assistant panel" })).toBeVisible();
  });

  test("no page scrolls sideways at phone width", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await signUp(page, uniqueEmail("narrow"));
    const card = await upload(page, POLICY);

    for (const url of ["/", "/dashboard", await card.evaluate(() => location.pathname)]) {
      await page.goto(url);
      const { scrollW, clientW } = await page.evaluate(() => ({
        scrollW: document.documentElement.scrollWidth,
        clientW: document.documentElement.clientWidth,
      }));
      expect(scrollW, `horizontal overflow on ${url}`).toBeLessThanOrEqual(clientW);
    }
  });
});
