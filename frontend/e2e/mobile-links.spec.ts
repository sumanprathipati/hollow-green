import { expect, test, type Page } from "@playwright/test";
import { openPublicAssessment, useTestProvider } from "./helpers";

async function noHorizontalScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

test("mobile layout has no horizontal scroll and controls stay usable", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Demo scenarios" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Public GitHub evidence" }),
  ).toBeVisible();
  await page.getByLabel("Release fixture").selectOption("rel-clean-001");
  const analyze = page.getByRole("button", { name: "Analyze release" });
  await expect(analyze).toBeEnabled();
  await expect(analyze).toBeVisible();
  await noHorizontalScroll(page);
});

test("AI panel stays readable on a narrow viewport", async ({ page }) => {
  await page.goto("/");
  await openPublicAssessment(page);
  await useTestProvider(page, "available");
  await page.getByRole("button", { name: "Generate evidence review" }).click();
  await expect(
    page.getByRole("heading", { name: "What the public evidence shows" }),
  ).toBeVisible();
  await noHorizontalScroll(page);
});

test("external source links carry noreferrer and accessible names", async ({
  page,
}) => {
  await page.goto("/");
  await openPublicAssessment(page);
  await useTestProvider(page, "available");
  await page.getByRole("button", { name: "Generate evidence review" }).click();
  await expect(
    page.getByRole("heading", { name: "Sources" }),
  ).toBeVisible();
  const links = page.locator('a[target="_blank"]');
  expect(await links.count()).toBeGreaterThan(0);
  for (let i = 0; i < (await links.count()); i += 1) {
    const link = links.nth(i);
    const rel = (await link.getAttribute("rel")) ?? "";
    expect(rel).toContain("noreferrer");
    const name =
      (await link.getAttribute("aria-label")) ?? (await link.textContent()) ?? "";
    expect(name.trim().length).toBeGreaterThan(0);
  }
});
