import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { analyzeFixture, openPublicAssessment } from "./helpers";

async function expectNoSeriousViolations(page: Page, context: string): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(
    blocking.map((v) => `${v.id}: ${v.help}`),
    `${context} has no serious/critical axe violations`,
  ).toEqual([]);
}

test("demo analyzed view has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await analyzeFixture(page, "rel-fragile-003");
  await expect(
    page.getByRole("heading", { name: "PROCEED WITH CAUTION" }),
  ).toBeVisible();
  await expectNoSeriousViolations(page, "demo");
});

test("public assessment view has no serious accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  await openPublicAssessment(page);
  await expectNoSeriousViolations(page, "public");
});

test("evidence tabs are keyboard operable", async ({ page }) => {
  await page.goto("/");
  await analyzeFixture(page, "rel-clean-001");
  await expect(page.getByRole("heading", { name: "PROCEED" })).toBeVisible();
  await page.getByRole("tab", { name: "Deductions" }).click();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Buffers" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.keyboard.press("End");
  await expect(page.getByRole("tab", { name: "Audit" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.keyboard.press("Home");
  await expect(page.getByRole("tab", { name: "Deductions" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});
