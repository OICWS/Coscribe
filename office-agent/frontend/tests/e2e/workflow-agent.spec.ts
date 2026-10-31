import { expect, test } from "@playwright/test";

// No model involved: these check how agent steps (decision 0028) read on a
// workflow's page and that one added in the editor saves as version 2.

test("a workflow's page shows its agent steps and what each may do", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e agent steps",
      kind: "manual",
      at: "",
      workflow: {
        version: 2,
        inputs: [{ name: "company", label: "Company" }],
        steps: [
          { id: "research", kind: "agent", title: "Research the company", goal: "Find news on {{company}}", tools: ["search_web"], sites: ["example.com"], save_as: "found" },
          { id: "write", kind: "agent", autonomy: "high", title: "Write the brief", goal: "Write a brief from {{found.report}}" },
        ],
      },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await expect(page.locator('[data-canvas-step="research"]')).toContainText("1 tool");
    const panel = page.getByTestId("workflow-permissions");
    await expect(panel).toContainText("Research the company · Within limits: can use Search web, open example.com");
    await expect(panel).toContainText("Write the brief · Broad: can use any of Coscribe’s tools");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});

test("an agent step added in the editor is saved, and makes the workflow version 2", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e add agent step",
      kind: "manual",
      at: "",
      workflow: { inputs: [], steps: [{ id: "list", kind: "tool", title: "List files", tool: "list_files", args: { path: "." }, save_as: "files" }] },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await page.getByRole("button", { name: "Edit steps" }).click();
    await page.getByRole("button", { name: "Add step" }).last().click();
    await page.getByRole("dialog", { name: "Add a step" }).getByText("Agent", { exact: true }).click();
    await page.getByLabel("Goal").fill("Summarise {{files}}");
    await page.locator("select", { hasText: "Add a tool…" }).selectOption("read_file");
    await page.getByRole("button", { name: "Add step" }).first().click();

    await expect(page.locator('[data-step="agent"]')).toContainText("1 tool");
    const tasks = await (await page.request.get("/api/scheduled-tasks")).json();
    const saved = tasks.find((t: { trigger_id: string }) => t.trigger_id === task.trigger_id);
    expect(saved.workflow.version).toBe(2);
    expect(saved.workflow.steps[1]).toMatchObject({ kind: "agent", autonomy: "bounded", tools: ["read_file"] });
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
