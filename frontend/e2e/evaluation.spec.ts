import { expect, test } from "@playwright/test";
import path from "node:path";
import { SAMPLES, signUp, uniqueEmail, uploadAndWait } from "./helpers";

test.describe("evaluation results", () => {
  test("a self-check runs on first open and can be re-run", async ({ page }) => {
    await signUp(page, uniqueEmail("eval"));
    const card = await uploadAndWait(page, path.join(SAMPLES, "Kanangra-Court-Medication-Management-Policy.pdf"));
    await card.click();

    await page.getByRole("link", { name: "Evaluation results" }).click();
    await expect(page).toHaveURL(/\/eval$/);

    // No ground truth exists for a just-uploaded document, so the automatic
    // self-check has to fire on its own.
    await expect(page.getByText("Automatic self-check")).toBeVisible({ timeout: 60_000 });
    for (const metric of ["Grounding", "Coverage", "Overall"]) {
      await expect(page.getByText(metric, { exact: true })).toBeVisible();
    }
    await expect(page.getByText(/^\d+%$/).first()).toBeVisible();

    // Regression: the label and the "latest" badge ran together as one word.
    await expect(page.getByText("Automatic self-checklatest")).toHaveCount(0);

    const runs = page.locator("text=Automatic self-check");
    const before = await runs.count();
    await page.getByRole("button", { name: "Re-evaluate" }).click();
    await expect(runs).toHaveCount(before + 1, { timeout: 60_000 });
  });
});
