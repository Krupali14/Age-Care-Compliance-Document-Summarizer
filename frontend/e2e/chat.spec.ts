import { expect, test } from "@playwright/test";
import path from "node:path";
import { SAMPLES, signUp, uniqueEmail, uploadAndWait } from "./helpers";

const POLICY = path.join(SAMPLES, "Sunrise-Grove-Incident-Management-Policy.pdf");

test.describe("AI assistant", () => {
  test.beforeEach(async ({ page }) => {
    await signUp(page, uniqueEmail("chat"));
    const card = await uploadAndWait(page, POLICY);
    await card.click();
    await expect(page.getByRole("log")).toBeVisible();
  });

  test("answers a real question and cites its sources", async ({ page }) => {
    // Regression: retrieval ranked by string similarity, so short headings beat the
    // provisions holding the answer and every question came back "I don't know."
    await page.getByRole("button", { name: "What deadlines are mentioned?" }).click();

    const answer = page.locator("[data-answer]").last();
    await expect(answer).not.toHaveText(/I don't know/i, { timeout: 120_000 });
    await expect(answer).not.toBeEmpty();

    // Every answer carries the section it came from, and the citation jumps there.
    const source = page.getByRole("button", { name: /^§/ }).first();
    await expect(source).toBeVisible();
    await source.click();
    await expect(page.getByRole("tab", { name: /^Sections/ })).toHaveAttribute("aria-selected", "true");
  });

  test("the newest answer is scrolled into view", async ({ page }) => {
    // Regression: the transcript kept its scroll position, so the second answer of
    // a conversation rendered ~900px below the fold and the screen looked unchanged.
    await page.getByRole("button", { name: "What are the major risks?" }).click();
    await expect(page.locator("[data-answer]")).toHaveCount(1, { timeout: 120_000 });

    const input = page.getByLabel("Ask a question about this document");
    await expect(input).toBeEnabled();
    await input.fill("Who is responsible for reporting a Priority 1 incident?");
    await input.press("Enter");
    await expect(page.locator("[data-answer]")).toHaveCount(2, { timeout: 120_000 });

    const distance = await page.getByRole("log").evaluate(
      (el) => el.scrollHeight - el.scrollTop - el.clientHeight,
    );
    expect(distance).toBeLessThan(40);
  });

  test("suggestions open the conversation and then get out of the way", async ({ page }) => {
    // Regression: the suggestions sat in a strip pinned above the composer for the
    // whole conversation, squeezing every answer into a narrow band.
    const suggestion = page.getByRole("button", { name: "What are the key compliance obligations?" });
    await expect(suggestion).toBeVisible();

    await suggestion.click();
    await expect(page.locator("[data-answer]")).toHaveCount(1, { timeout: 120_000 });
    await expect(suggestion).toHaveCount(0);

    // Clearing the conversation brings them back.
    await page.getByRole("button", { name: "New conversation" }).click();
    await expect(page.getByRole("button", { name: "What are the key compliance obligations?" })).toBeVisible();
  });

  test("the composer refuses an empty question and caps a huge one", async ({ page }) => {
    const input = page.getByLabel("Ask a question about this document");
    const send = page.getByRole("button", { name: "Send question" });
    await expect(send).toBeDisabled();

    await input.fill("   ");
    await expect(send).toBeDisabled();

    // Regression: unbounded input was forwarded to the model verbatim.
    await input.fill("x".repeat(5000));
    expect((await input.inputValue()).length).toBe(2000);
  });

  test("answers render as formatted Markdown, not raw asterisks", async ({ page }) => {
    await page.getByRole("button", { name: "What are the key compliance obligations?" }).click();
    const answer = page.locator("[data-answer]").last();
    await expect(answer).not.toBeEmpty({ timeout: 120_000 });
    await expect(answer).not.toContainText("**");
  });
});
