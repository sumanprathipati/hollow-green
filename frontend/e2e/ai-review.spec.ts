import { expect, test } from "@playwright/test";
import { BANNED_PAGE_TOKENS, openPublicAssessment, useTestProvider } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await openPublicAssessment(page);
});

test("unavailable provider shows setup message, assessment intact", async ({ page }) => {
  await expect(
    page.getByRole("heading", { name: "AI-assisted evidence review" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Generate evidence review" }).click();
  await expect(page.getByText("AI review is not configured").first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "ELEVATED CHANGE RISK — INVESTIGATE" }),
  ).toBeVisible();
  for (const token of BANNED_PAGE_TOKENS) {
    await expect(page.locator("body")).not.toContainText(token);
  }
});

test("fake available provider renders sections, chips, sources, regenerate", async ({
  page,
}) => {
  await useTestProvider(page, "available");
  await page.getByRole("button", { name: "Generate evidence review" }).click();
  await expect(
    page.getByRole("heading", { name: "What the public evidence shows" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Why the deterministic assessment is ELEVATED CHANGE RISK — INVESTIGATE",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Evidence gaps and what cannot be determined" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Suggested human review checks" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  const chip = page
    .locator('section[aria-label="AI-assisted evidence review"] a[target="_blank"]')
    .first();
  await expect(chip).toBeVisible();
  const href = await chip.getAttribute("href");
  expect(href).toContain("https://github.com/octocat/Hello-World");
  await expect(
    page.getByRole("button", { name: "Regenerate evidence review" }),
  ).toBeVisible();
  for (const token of BANNED_PAGE_TOKENS) {
    await expect(page.locator("body")).not.toContainText(token);
  }
});

test("blocked response shows message without generated text", async ({ page }) => {
  await useTestProvider(page, "blocked");
  await page.getByRole("button", { name: "Generate evidence review" }).click();
  await expect(page.getByText("did not meet evidence-grounding requirements")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("safe to deploy");
  await expect(
    page.getByRole("heading", { name: "ELEVATED CHANGE RISK — INVESTIGATE" }),
  ).toBeVisible();
});
