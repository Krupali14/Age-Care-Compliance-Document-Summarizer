import { expect, test } from "@playwright/test";
import path from "node:path";
import { SAMPLES, signUp, uniqueEmail, uploadAndWait } from "./helpers";

test.describe("phone layout", () => {
  test("the assistant opens as a sheet and closes on Escape", async ({ page }) => {
    await signUp(page, uniqueEmail("sheet"));
    const card = await uploadAndWait(page, path.join(SAMPLES, "Thornbury-Food-Nutrition-and-Dining-Policy.pdf"));
    await card.click();

    await page.getByRole("button", { name: "Ask AI" }).click();
    const sheet = page.getByRole("dialog", { name: "AI assistant" });
    await expect(sheet).toBeVisible();

    // Regression: the sheet answered to no key and left the page behind it
    // scrolling underneath.
    await expect(page.locator("body")).toHaveCSS("overflow", "hidden");
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
    await expect(page.locator("body")).not.toHaveCSS("overflow", "hidden");
  });
});
