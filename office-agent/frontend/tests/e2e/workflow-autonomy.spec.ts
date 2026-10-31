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
    const setting = page.getByTestId("autonomy-setting");
    await setting.getByRole("radio", { name: "Fixed" }).click();
    await expect(setting).toContainText(
      'doesn\'t allow "Write the brief"; raise it to proactive',
    );
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
    const report = page.getByTestId("run-report");
    await expect(report).toContainText("Report · Fixed");
    await expect(report).toContainText("Every step was done.");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
