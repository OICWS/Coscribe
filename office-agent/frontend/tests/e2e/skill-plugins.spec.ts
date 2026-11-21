import { expect, test, type Page } from "@playwright/test";

type PluginSummary = { title: string; skills: string[] };

// Add leaves the plugin's skills in the workspace's skills folder, where the next run would find
// the plugin already added and no Add button to press.
async function removeLegalSkills(page: Page): Promise<void> {
  const plugins = (await (await page.request.get("/api/skills/plugins")).json()) as PluginSummary[];
  const legal = plugins.find((plugin) => plugin.title.startsWith("Legal"));
  if (!legal) return;
  const installed = new Set(
    ((await (await page.request.get("/api/skills")).json()) as { name: string; source: string }[])
      .filter((skill) => skill.source === "anthropic")
      .map((skill) => skill.name),
  );
  for (const name of legal.skills) {
    if (installed.has(name)) await page.request.delete(`/api/skills/${encodeURIComponent(name)}`);
  }
}

test.beforeEach(async ({ page }) => removeLegalSkills(page));
test.afterEach(async ({ page }) => removeLegalSkills(page));

test("Discover lists plugins; a plugin can be previewed file by file before Add installs all its skills", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByText("Skills", { exact: true }).first().click();
  await page.getByRole("button", { name: "Discover", exact: true }).first().click();

  const card = page.getByRole("button", { name: /^Legal by Anthropic/ });
  await expect(card).toBeVisible();
  await card.click();

  // Nothing is added yet, but SKILL.md and the other files can be read.
  await expect(page.getByRole("button", { name: "Add", exact: true })).toBeVisible();
  await page.getByRole("button", { name: /^Contents ·/ }).click();
  await expect(page.getByText(/^\/skills\/.+\/SKILL\.md$/)).toBeVisible();
  await expect(page.getByText("Loading...")).toHaveCount(0, { timeout: 20_000 });

  await page.getByRole("button", { name: /^Skills ·/ }).click();
  await expect(page.getByText("review-contract")).toBeVisible();

  await page.getByRole("button", { name: /^Connectors ·/ }).click();
  await expect(page.getByText("Slack")).toBeVisible();

  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("Added", { exact: true })).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Discover" }).first().click();
  await page.getByRole("button", { name: "Yours", exact: true }).click();
  await expect(page.getByText("review-contract").first()).toBeVisible();
});
