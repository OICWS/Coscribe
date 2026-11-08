import { expect, test, type APIRequestContext } from "@playwright/test";

// No model involved: a task runs another as one of its steps, passing a value in and getting its
// results back, and the run page nests the called task's steps; then the task page compares two
// versions of its workflow and restores the first as a new one (decision 0035).

interface Made {
  trigger_id: string;
}

async function create(request: APIRequestContext, name: string, workflow: object): Promise<Made> {
  const made = await (
    await request.post("/api/scheduled-tasks", { data: { name, kind: "manual", at: "", workflow } })
  ).json();
  expect(made.trigger_id, JSON.stringify(made)).toBeTruthy();
  return made;
}

async function lastRun(request: APIRequestContext, id: string) {
  const tasks = await (await request.get("/api/scheduled-tasks")).json();
  const runs = tasks.find((t: Made) => t.trigger_id === id).runs;
  return runs[runs.length - 1];
}

test("a task runs another, and its versions can be compared and restored", async ({ page }) => {
  const called = await create(page.request, "e2e called", {
    inputs: [{ name: "who", label: "Who asked", type: "text" }],
    memory: [{ name: "asked", label: "Last asked", type: "text" }],
    steps: [
      { id: "list", kind: "tool", title: "List the workspace", tool: "list_files", args: {}, save_as: "found" },
      { id: "keep", kind: "remember", title: "Note who asked", name: "asked", value: "{{who}}" },
    ],
  });
  const step = {
    id: "call",
    kind: "run_task",
    title: "Run the lister",
    task: called.trigger_id,
    inputs: { who: "the caller" },
    save_as: "listed",
  };
  const caller = await create(page.request, "e2e caller", { inputs: [], steps: [step] });
  const id = caller.trigger_id;
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    await expect(page.locator('[data-plain-step="call"]')).toContainText("Runs your task “e2e called”");
    await expect(page.getByTestId("workflow-permissions")).toContainText("Runs your task “e2e called”");

    await page.request.post(`/api/scheduled-tasks/${id}/run`, { data: {} });
    await expect.poll(async () => (await lastRun(page.request, id)).status, { timeout: 30_000 }).toBe("completed");
    const run = await lastRun(page.request, id);
    expect(run.versions).toEqual([1]);
    expect(run.called.call).toMatchObject({ task: called.trigger_id, name: "e2e called", version: 1 });
    const memory = await (await page.request.get(`/api/scheduled-tasks/${called.trigger_id}/memory`)).json();
    expect(memory.memory.asked.value).toBe("the caller");

    await page.goto(`/?thread=scheduled-${id}-${run.run_id}`);
    await page.getByRole("button", { name: "Detailed", exact: true }).click();
    const row = page.locator('[data-run-step="call"]').first();
    await expect(row).toContainText("Ran “e2e called” · version 1", { timeout: 30_000 });
    await row.getByRole("button", { name: /^Show the 2 steps/ }).click();
    await expect(page.locator('[data-run-step="call/keep"]')).toContainText("Note who asked");
    await expect(page.getByTestId("report-tasks")).toContainText("“e2e called” · version 1 -- done");

    // A second version, then the first restored as a third.
    await page.request.patch(`/api/scheduled-tasks/${id}`, {
      data: { workflow: { inputs: [], steps: [{ ...step, title: "Run the lister again" }] } },
    });
    await page.goto(`/?view=scheduled&task=${id}`);
    await page.getByRole("button", { name: "Detailed", exact: true }).click();
    const rows = page.getByTestId("version-row");
    await expect(rows).toHaveCount(2);
    await expect(rows.first()).toContainText("Version 2");
    await rows.nth(1).getByRole("button", { name: "Compare" }).click();
    await expect(page.getByTestId("version-diff")).toContainText("Changed");
    await expect(page.getByTestId("version-diff")).toContainText("Run the lister again");
    await rows.nth(1).getByRole("button", { name: "Restore" }).click();
    await page.getByRole("button", { name: "Restore", exact: true }).last().click();
    await expect(rows).toHaveCount(3);
    await expect(rows.first()).toContainText("Restored from version 1");
    const versions = await (await page.request.get(`/api/scheduled-tasks/${id}/versions`)).json();
    expect(versions.current).toBe(3);
    expect(versions.versions[0].workflow.steps[0].title).toBe("Run the lister");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
    await page.request.delete(`/api/scheduled-tasks/${called.trigger_id}`);
  }
});
