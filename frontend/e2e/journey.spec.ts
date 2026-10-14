import { expect, test, type Page } from "@playwright/test";

/** Drives a trial to the verdict, fast-forwarding lines and answering every window. */
async function playToVerdict(page: Page, final: "Guilty" | "Not guilty", gate = true) {
  const rise = page.getByRole("button", { name: "All rise" });
  if (gate) await rise.click();
  await page.waitForTimeout(1500); // let the previous verdict card close after a replay
  const deadline = Date.now() + 180_000;
  while (Date.now() < deadline) {
    if (await page.getByText("Retry with a different verdict").isVisible().catch(() => false)) return;
    const dialog = page.locator("[role=dialog]");
    if (await dialog.isVisible().catch(() => false)) {
      const objection = dialog.locator("button.animate-pulse-gold");
      if (await objection.isVisible().catch(() => false)) await objection.click();
      const finalBtn = dialog.getByRole("button", { name: new RegExp(`^${final}`) });
      if (await finalBtn.isVisible().catch(() => false)) await finalBtn.click();
      else await dialog.locator("button.rounded-xl").first().click();
      await page.waitForTimeout(600);
      continue;
    }
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(200);
  }
  throw new Error("trial did not reach a verdict in time");
}

test("landing communicates the idea and links to the showcase", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Order in the court.");
  await expect(page.getByRole("link", { name: "Put something on trial" })).toBeVisible();
  await page.getByRole("link", { name: "Watch a ridiculous case" }).click();
  await expect(page.getByRole("heading", { name: "The People vs. JavaScript" })).toBeVisible();
});

test("showcase: jury vote drives the verdict, replay keeps history", async ({ page }) => {
  await page.goto("/case/the-people-vs-javascript/court?mode=jury");
  await playToVerdict(page, "Guilty");
  await expect(page.getByRole("heading", { level: 2 }).filter({ hasText: "Guilty of" })).toBeVisible();
  await page.getByRole("button", { name: "Retry with a different verdict" }).click();
  await playToVerdict(page, "Not guilty", false);
  await expect(page.getByText("Not guilty.", { exact: false }).first()).toBeVisible();
});

test("file a new case end to end in mock mode", async ({ page }) => {
  await page.goto("/file");
  await page.getByLabel("Who or what is being accused").fill("The office printer");
  await page.getByRole("button", { name: "Continue →" }).click();
  await page.getByPlaceholder("Destroying my dreams every single morning.").fill("Jamming only when I am already late");
  await page.getByRole("button", { name: "Continue →" }).click();
  await page.getByRole("button", { name: /Quick hearing/ }).click();
  await page.getByRole("button", { name: "File the case" }).click();
  await expect(page.getByRole("link", { name: "Enter the courtroom →" })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("radio", { name: /Spectator/ }).click();
  await page.getByRole("link", { name: "Enter the courtroom →" }).click();
  await playToVerdict(page, "Guilty");
});
