import { expect, test } from "@playwright/test";

// No model involved: the task's autonomy switch and a finished run's report (decision 0030).

test("the autonomy switch refuses a level below the task's steps", async ({
  page,
}) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e autonomy",
      kind: "manual",
      at: "",
      workflow: {
        version: 2,
        inputs: [],
        steps: [
          {
            id: "write",
            kind: "agent",
            autonomy: "high",
            title: "Write the brief",
            goal: "Write a brief",
          },
        ],
      },
    },
  });
  const task = await created.json();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    await page.getByRole("button", { name: "Detailed" }).click();
    await page.getByRole("group", { name: "Workflow view" }).getByRole("button", { name: "Settings" }).click();
    const setting = page.getByTestId("autonomy-setting");
    // Below what its agent step needs, a level can't be picked.
    await expect(setting.getByRole("radio", { name: "Fixed" })).toBeDisabled();
    await setting.getByRole("radio", { name: "Proactive" }).click();
    await expect(
      setting.getByRole("radio", { name: "Proactive" }),
    ).toHaveAttribute("aria-checked", "true");
    const tasks = await (await page.request.get("/api/scheduled-tasks")).json();
    const saved = tasks.find(
      (t: { trigger_id: string }) => t.trigger_id === task.trigger_id,
    );
    expect(saved.workflow.autonomy).toBe("proactive");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});

test("a finished run shows its report", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e run report",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [],
        steps: [
          {
            id: "list",
            kind: "tool",
            title: "List files",
            tool: "list_files",
            args: { path: "." },
          },
        ],
      },
    },
  });
  const task = await created.json();
  try {
    const started = await (
      await page.request.post(`/api/scheduled-tasks/${task.trigger_id}/run`, {
        data: {},
      })
    ).json();
    await expect
      .poll(async () => {
        const tasks = await (
          await page.request.get("/api/scheduled-tasks")
        ).json();
        const saved = tasks.find(
          (t: { trigger_id: string }) => t.trigger_id === task.trigger_id,
        );
        return saved.runs.find(
          (r: { run_id: string }) => r.run_id === started.run.run_id,
        ).status;
      })
      .toBe("completed");
    await page.goto(`/?thread=${started.run.thread_id}`);
    // The report is part of the detailed run.
    await page.getByRole("button", { name: "Detailed", exact: true }).click();
    const report = page.getByTestId("run-report");
    await expect(report).toContainText("Report · Fixed");
    await expect(report).toContainText("Every step was done.");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
