import { expect, test } from "@playwright/test";
import path from "node:path";
import { SAMPLES, signUp, uniqueEmail, uploadAndWait } from "./helpers";

const POLICY = path.join(SAMPLES, "Sunrise-Grove-Incident-Management-Policy.pdf");

/** The "Ask next" chips currently on offer, excluding the § citation chips. */
async function followUpTexts(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() => {
    const log = document.querySelector("[role=log]");
    if (!log) return [];
    return [...log.querySelectorAll("button")]
      .map((b) => b.textContent?.trim() ?? "")
      .filter((t) => t && !t.startsWith("§"));
  });
}

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

  test("suggestions stay available and follow the conversation", async ({ page }) => {
    // Regression, twice over. The suggestions first sat in a strip pinned above the
    // composer, which cost the answer area its height for the whole conversation.
    // Removing that strip then removed the feature: once a conversation started
    // there was nothing to click at all. They now live in the scroll flow beneath
    // the newest answer, and they change as the conversation moves.
    const opener = page.getByRole("button", { name: "What are the key compliance obligations?" });
    await expect(opener).toBeVisible();

    await opener.click();
    await expect(page.locator("[data-answer]")).toHaveCount(1, { timeout: 120_000 });

    // Still suggestions on offer — but not the one just asked.
    const askNext = page.getByText("Ask next");
    await expect(askNext).toBeVisible();
    await expect(opener).toHaveCount(0);

    // They live inside the transcript, so they scroll with it rather than taking
    // fixed space from the answer.
    expect(await askNext.evaluate((el) => !!el.closest("[role=log]"))).toBe(true);

    const firstSet = await followUpTexts(page);
    expect(firstSet.length).toBeGreaterThan(0);

    await page.getByRole("button", { name: firstSet[0] }).click();
    await expect(page.locator("[data-answer]")).toHaveCount(2, { timeout: 120_000 });

    const secondSet = await followUpTexts(page);
    expect(secondSet).not.toContain(firstSet[0]);   // asked, so dropped
    expect(secondSet).not.toEqual(firstSet);        // and the rest moved on

    // Clearing the conversation returns to the openers.
    await page.getByRole("button", { name: "Start a new conversation" }).click();
    await expect(page.getByRole("button", { name: "What are the key compliance obligations?" })).toBeVisible();
  });

  test("suggestions match what the document actually contains", async ({ page }) => {
    // The old list was four hardcoded strings, so a document with no deadlines in
    // it was still offered "What deadlines are mentioned?".
    const counts = await page.evaluate(() =>
      [...document.querySelectorAll("[role=tab]")].map((t) => t.getAttribute("aria-label") ?? t.textContent ?? ""),
    );
    const hasRisks = !/Risks, 0 items/.test(counts.join(" "));

    const openers = await page.locator("[role=log] button").allInnerTexts();
    expect(openers.some((q) => /obligations/i.test(q))).toBe(true);
    if (!hasRisks) {
      expect(openers.some((q) => /risks/i.test(q))).toBe(false);
    }
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
