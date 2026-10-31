import { expect, test } from "@playwright/test";

// No model involved: a workflow's page opens on its canvas, which draws
// branches and loops from the workflow's structure.

test("a workflow's page shows it as a canvas, and a step on it opens in the editor", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e workflow canvas",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [{ name: "folder", label: "Folder" }],
        steps: [
          { id: "list", kind: "tool", title: "List the reports", tool: "list_files", args: { path: "{{folder}}" }, save_as: "files" },
          {
            id: "each",
            kind: "loop",
            title: "Go through each report",
            over: "files",
            item: "report",
            steps: [{ id: "read", kind: "tool", title: "Read the report", tool: "read_file", args: { path: "{{report}}" } }],
          },
          {
            id: "any",
            kind: "branch",
            title: "Were there any?",
            condition: { left: { count: "files" }, op: "gt", right: { value: 0 } },
            then: [{ id: "ok", kind: "approval", title: "Look them over", message: "Check the reports." }],
            otherwise: [],
          },
        ],
      },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    const canvas = page.getByTestId("workflow-canvas");
    await expect(canvas).toContainText("Start");
    await expect(canvas).toContainText("Repeats for each item");
    await expect(canvas.locator('[data-canvas-step="read"]')).toBeVisible();
    await expect(canvas).toContainText("Then");
    await expect(canvas).toContainText("Otherwise");
    await expect(canvas).toContainText("Done");

    await canvas.locator('[data-canvas-step="ok"]').click();
    await expect(page.getByTestId("workflow-canvas")).toHaveCount(0);
    await expect(page.locator('[data-step="ok"]')).toContainText("Step name");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
