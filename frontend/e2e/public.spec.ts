import { expect, test } from "@playwright/test";
import { BANNED_PAGE_TOKENS, openPublicAssessment } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Release Confidence Command Center" }),
  ).toBeVisible();
});

test("public hero shows first with sentence, recommendation, and completeness", async ({
  page,
}) => {
  await openPublicAssessment(page);
  await expect(
    page.getByText("Public repository evidence only — deployment readiness cannot be determined.").first(),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "ELEVATED CHANGE RISK — INVESTIGATE" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Evidence completeness" }),
  ).toBeVisible();
  await expect(page.getByText("sufficient").first()).toBeVisible();
  await expect(page.getByText("Unavailable operational signals")).toBeVisible();
  await expect(page.getByText("health").first()).toBeVisible();
  for (const token of BANNED_PAGE_TOKENS) {
    await expect(page.locator("body")).not.toContainText(token);
  }
});
