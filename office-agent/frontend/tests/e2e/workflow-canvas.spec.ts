import { expect, test } from "@playwright/test";

// No model involved: a workflow's page opens on its simple view, a canvas in plain words; its
// detailed view draws the same structure with each step's tool and values.

test("a workflow's page shows it as a canvas in plain words, then in detail, and a step on it opens in the editor", async ({ page }) => {
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
    const simple = page.getByTestId("task-simple-view");
    await expect(simple.locator('[data-plain-step="list"]')).toContainText("Lists the files in Folder");
    await expect(simple.locator('[data-plain-step="each"]')).toContainText("For each report in the files");
    await expect(simple.locator('[data-plain-step="read"]')).toContainText("Reads the report");
    await expect(simple.locator('[data-plain-step="any"]')).toContainText("If the number of the files is more than 0");
    await expect(simple.locator('[data-plain-step="ok"]')).toContainText("Waits for your OK");
    await simple.getByRole("button", { name: "Show the flowchart" }).click();
    await expect(simple.getByTestId("workflow-canvas")).toContainText("Repeats for each report");
    await expect(simple.getByTestId("workflow-canvas")).toContainText("If so");
    await expect(simple).not.toContainText("list_files");
    await expect(simple).not.toContainText("{{");

    await page.getByRole("button", { name: "Detailed" }).click();
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
