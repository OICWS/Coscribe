import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

// No model involved: a workflow task is created through the API, so these
// check what the page shows and does with permissions.

test("a workflow's page lists what it can touch, and is plain about scripts", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e permissions list",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [],
        steps: [
          { id: "open", kind: "tool", title: "Open the ERP", tool: "browser_navigate", args: { url: "https://erp.example.com/start" } },
          { id: "sum", kind: "script", title: "Summarise", code: "print('{}')" },
        ],
      },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await page.getByRole("button", { name: "Detailed" }).click();
    const panel = page.getByTestId("workflow-permissions");
    await expect(panel).toContainText("erp.example.com");
    await expect(panel).toContainText("Summarise");
    await expect(panel).toContainText("aren’t sandboxed");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});

test("a run that needs a folder it hasn't been allowed stops, and carries on once allowed", async ({ page }) => {
  const folder = mkdtempSync(join(tmpdir(), "coscribe-e2e-perm-"));
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e permission wait",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [{ name: "dest", label: "Where to save" }],
        steps: [{ id: "save", kind: "tool", title: "Save the report", tool: "write_file", args: { path: "{{dest}}", content: "report" } }],
      },
    },
  });
  const task = await created.json();
  try {
    const started = await page.request.post(`/api/scheduled-tasks/${task.trigger_id}/run`, {
      data: { inputs: { dest: join(folder, "out.txt") } },
    });
    const run = (await started.json()).run;
    await page.goto(`/?thread=${run.thread_id}`);

    await expect(page.getByTestId("permission-request")).toContainText(folder);
    await expect(page.getByTestId("run-result")).toContainText("Waiting for your OK at");
    await page.getByRole("button", { name: "Allow and continue" }).click();

    await expect(page.getByTestId("permission-request")).toHaveCount(0);
    await expect.poll(() => readFileSync(join(folder, "out.txt"), "utf-8").toString(), { timeout: 15_000 }).toBe("report");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
    rmSync(folder, { recursive: true, force: true });
  }
});
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
