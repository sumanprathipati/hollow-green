import { expect, type Page } from "@playwright/test";

/** Analyze a demo fixture and wait for its decision hero. */
export async function analyzeFixture(page: Page, releaseId: string): Promise<void> {
  await page.getByLabel("Release fixture").selectOption(releaseId);
  await page.getByRole("button", { name: "Analyze release" }).click();
}

/** Switch to public mode, pick the allowlisted repo, refresh, await the hero. */
export async function openPublicAssessment(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Public GitHub evidence" }).click();
  await page.getByLabel("Repository").selectOption("octocat/Hello-World");
  await page.getByRole("button", { name: "Refresh assessment" }).click();
  await expect(
    page.getByRole("heading", { name: "ELEVATED CHANGE RISK — INVESTIGATE" }),
  ).toBeVisible();
}

/** Route evidence-review POSTs through the env-gated test provider. */
export async function useTestProvider(
  page: Page,
  mode: "available" | "blocked" | "error",
): Promise<void> {
  await page.route("**/evidence-review*", async (route) => {
    const url = new URL(route.request().url());
    url.searchParams.set("test_provider", mode);
    await route.continue({ url: url.toString() });
  });
}

export const BANNED_PAGE_TOKENS = [
  "PROCEED",
  "ROLLBACK VERIFIED",
  "HOLD / INVESTIGATE",
  "clean_success",
  "recovered_success",
  "fragile_success",
  "release approval",
  "deployment approval",
  "safe to deploy",
  "deploy now",
  "production ready",
];
