import { expect, test } from "@playwright/test";
import { analyzeFixture } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Release Confidence Command Center" }),
  ).toBeVisible();
});

test("loads brand, badge, and fixture picker", async ({ page }) => {
  await expect(page.getByText("Synthetic demo environment")).toBeVisible();
  await expect(page.getByLabel("Release fixture")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze release" })).toBeVisible();
});

test("fragile fixture shows decision hero with 23 critical", async ({ page }) => {
  await analyzeFixture(page, "rel-fragile-003");
  await expect(
    page.getByRole("heading", { name: "PROCEED WITH CAUTION" }),
  ).toBeVisible();
  await expect(page.getByText(/Reserve Level 23 \/ 100/)).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Reserve Level" }),
  ).toHaveAttribute("aria-valuenow", "23");
  await expect(
    page.getByRole("heading", { name: "AI-assisted evidence review" }),
  ).toHaveCount(0);
});

const ALL_FIXTURES: Array<[string, string]> = [
  ["rel-clean-001", "PROCEED"],
  ["rel-recovered-002", "PROCEED WITH CAUTION"],
  ["rel-fragile-003", "PROCEED WITH CAUTION"],
  ["rel-rollback-005", "ROLLBACK VERIFIED"],
  ["rel-failed-006", "HOLD / INVESTIGATE"],
];

for (const [releaseId, decision] of ALL_FIXTURES) {
  test(`fixture ${releaseId} recommends ${decision}`, async ({ page }) => {
    await analyzeFixture(page, releaseId);
    await expect(page.getByRole("heading", { name: decision })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "AI-assisted evidence review" }),
    ).toHaveCount(0);
  });
}
