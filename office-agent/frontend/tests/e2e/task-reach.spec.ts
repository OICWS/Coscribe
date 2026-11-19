import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

// No model involved: a task's folder input is checked against what the task reaches, a folder
// outside it is allowed for this task only, and the task's page lists it and takes it back.

test("a folder outside a task's reach is allowed for that task from its folder input", async ({ page }) => {
  const outside = mkdtempSync(join(tmpdir(), "coscribe-e2e-reach-"));
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e task reach",
      kind: "manual",
      at: "",
      workflow: {
        version: 2,
        inputs: [{ name: "save_to", label: "Save report to", type: "folder" }],
        steps: [{ id: "list", kind: "tool", title: "List the folder", tool: "list_files", args: { path: "{{save_to}}" } }],
      },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await page.getByRole("button", { name: "Run now" }).click();
    const dialog = page.locator("form").filter({ has: page.getByRole("heading", { name: "Run e2e task reach" }) });
    await dialog.getByRole("button", { name: "Choose a folder for Save report to" }).click();
    await expect(dialog.getByRole("menu", { name: "Folders for Save report to" })).toContainText("Workspace ·");
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel("Save report to", { exact: true }).fill("reports");
    await expect(dialog.getByText("In the workspace.")).toBeVisible();
    await dialog.getByLabel("Save report to", { exact: true }).fill(outside);
    await expect(dialog.getByText(`This task can’t use ${outside} yet`)).toBeVisible();
    await dialog.getByRole("button", { name: "Only this task" }).click();
    await expect(dialog.getByText(/a folder allowed for this task\./)).toBeVisible();
    const reach = await (await page.request.get(`/api/scheduled-tasks/${task.trigger_id}/reach`)).json();
    expect(reach.task).toContain(outside);
    await dialog.getByRole("button", { name: "Cancel" }).click();

    await page.getByRole("tab", { name: "Settings" }).click();
    const section = page.getByRole("region", { name: "What this task can reach" });
    await expect(section).toContainText("this task only · read and write");
    await section.getByRole("button", { name: `Remove ${outside}` }).click();
    await expect(section).not.toContainText("this task only · read and write");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
