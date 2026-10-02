import { expect, test } from "@playwright/test";

test("api-unavailable shows message and retry, then recovers", async ({ page }) => {
  await page.route("**/v1/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByText("API unavailable").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry connection" })).toBeVisible();
  await page.unrouteAll({ behavior: "wait" });
  // The E2E backend serves fixtures; retry must recover the picker.
  await page.getByRole("button", { name: "Retry connection" }).click();
  await expect(page.getByLabel("Release fixture")).toBeVisible();
});
