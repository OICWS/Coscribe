import { expect, test } from "@playwright/test";

test("A task of written instructions has its own step limit, changed in its form", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: { name: `Steps ${Date.now()}`, kind: "manual", at: "", prompt: "Say hello." },
  });
  expect(created.ok()).toBeTruthy();
  const task = await created.json();
  expect(task.max_steps).toBe(150);

  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await expect(page.getByText("A run stops after 150 steps.")).toBeVisible();

    await page.getByRole("button", { name: "Edit", exact: true }).click();
    const steps = page.getByLabel("Most steps");
    await expect(steps).toHaveValue("150");
    await steps.fill("40");
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(page.getByText("A run stops after 40 steps.")).toBeVisible();
    const saved = await (await page.request.get("/api/scheduled-tasks")).json();
    expect(saved.find((t: { trigger_id: string }) => t.trigger_id === task.trigger_id).max_steps).toBe(40);
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
