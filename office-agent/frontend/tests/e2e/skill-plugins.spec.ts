import { expect, test, type Page } from "@playwright/test";

type PluginSummary = { title: string; skills: string[] };

// Add leaves the plugin's skills in the workspace's skills folder, where the next run would find
// the plugin already added and no Add button to press.
async function removeLegalSkills(page: Page): Promise<void> {
  const plugins = (await (await page.request.get("/api/skills/plugins")).json()) as PluginSummary[];
  const legal = plugins.find((plugin) => plugin.title.startsWith("Legal"));
  if (!legal) return;
  const installed = (await (await page.request.get("/api/skills")).json()) as { name: string; source: string }[];
  for (const skill of installed) {
    if (skill.source === "anthropic" && legal.skills.includes(skill.name)) {
      expect(await page.request.delete(`/api/skills/${encodeURIComponent(skill.name)}`)).toBeOK();
    }
  }
}

test.beforeEach(async ({ page }) => removeLegalSkills(page));
test.afterEach(async ({ page }) => removeLegalSkills(page));

test("Discover lists plugins; a plugin can be previewed file by file before Add installs all its skills", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Plugins", exact: true }).click();
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
  await page.getByRole("button", { name: /^review-contract / }).click();
  await expect(page.getByText("/skills/review-contract/SKILL.md", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Contract Review Against Playbook/i })).toBeVisible();

  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("Added", { exact: true })).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Discover" }).first().click();
  await page.getByRole("button", { name: "Yours", exact: true }).click();
  for (const skill of ["review-contract", "triage-nda", "compliance-check", "legal-risk-assessment", "legal-response", "meeting-briefing"]) {
    await expect(page.getByRole("button", { name: `Open ${skill}`, exact: true })).toBeVisible();
  }
});
