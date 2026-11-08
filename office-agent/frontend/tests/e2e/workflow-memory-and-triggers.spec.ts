import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { pickOption } from "./helpers";

// No model involved: a task keeps a value only when its run finishes, the next run reads it and
// ends quietly, and a person clears it on the task page; then the task is set to run when a file
// arrives in a folder (decision 0034). The folder watch itself is tested in pytest, since it
// needs two scheduler polls.

async function task(request: APIRequestContext, id: string) {
  const tasks = await (await request.get("/api/scheduled-tasks")).json();
  return tasks.find((t: { trigger_id: string }) => t.trigger_id === id);
}

async function runOnce(request: APIRequestContext, id: string, count: number) {
  await request.post(`/api/scheduled-tasks/${id}/run`, { data: {} });
  await expect
    .poll(
      async () => {
        const runs = (await task(request, id)).runs;
        return runs.reduce((sum: number, r: { quiet?: number }) => sum + Math.max(r.quiet ?? 0, 1), 0) >= count
          ? runs[runs.length - 1].status
          : "pending";
      },
      { timeout: 30_000 },
    )
    .toBe("completed");
  const runs = (await task(request, id)).runs;
  return runs[runs.length - 1];
}

test("a task remembers between runs and ends quietly when there is nothing to do", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e memory",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [],
        memory: [{ name: "checked", label: "Last checked", type: "text" }],
        steps: [
          {
            id: "fresh",
            kind: "check",
            title: "Not checked yet",
            otherwise: "end",
            conditions: [{ left: { ref: "memory.checked" }, op: "empty" }],
          },
          { id: "keep", kind: "remember", title: "Note the day", name: "checked", value: "{{run.date}}" },
        ],
      },
    },
  });
  const made = await created.json();
  expect(made.trigger_id, JSON.stringify(made)).toBeTruthy();
  const id = made.trigger_id;
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    await expect(page.locator('[data-plain-step="fresh"]')).toContainText("Ends the run quietly");
    await expect(page.locator('[data-plain-step="keep"]')).toContainText("Keeps “Last checked” for the next run");
    const row = page.getByTestId("memory-row");
    await expect(row).toContainText("not kept yet");

    const first = await runOnce(page.request, id, 1);
    expect(first.quiet ?? 0).toBe(0);
    const memory = await (await page.request.get(`/api/scheduled-tasks/${id}/memory`)).json();
    const today = memory.memory.checked.value;
    expect(today).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    const second = await runOnce(page.request, id, 2);
    expect(second.quiet).toBe(1);
    await page.reload();
    await expect(row).toContainText(today);
    await expect(row).toContainText("kept by a run");
    await expect(page.getByText("Nothing new").first()).toBeVisible();

    await page.goto(`/?thread=scheduled-${id}-${second.run_id}`);
    await expect(page.getByText(/“Not checked yet” found\s+nothing to do/)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('[data-run-row="keep"]')).toHaveAttribute("data-run-status", "not_reached");

    // Cleared, the next run starts from the first value again and keeps a new one.
    await page.goto(`/?view=scheduled&task=${id}`);
    await row.getByRole("button", { name: "Clear" }).click();
    await expect(row).toContainText("not kept yet");
    const third = await runOnce(page.request, id, 3);
    expect(third.quiet ?? 0).toBe(0);
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
  }
});

test("a workflow task can run when a file arrives in a folder", async ({ page }) => {
  const inbox = mkdtempSync(join(tmpdir(), "coscribe-e2e-inbox-"));
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e folder",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [{ name: "doc", label: "New report", type: "file" }],
        steps: [{ id: "list", kind: "tool", title: "List what is there", tool: "list_files", args: {} }],
      },
    },
  });
  const made = await created.json();
  const id = made.trigger_id;
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    await page.getByRole("button", { name: "Edit" }).first().click();
    await pickOption(page.getByLabel("Frequency"), "When a file arrives in a folder");
    await page.getByLabel("Folder to watch").fill(inbox);
    await page.getByLabel("File name pattern").fill("*.pdf");
    await page.getByRole("button", { name: "Save" }).click();

    await expect(page.getByText("When a *.pdf file arrives in").first()).toBeVisible();
    await expect(page.getByText("Works on")).toBeVisible();
    await expect(page.getByText("the new file that arrived in the folder")).toBeVisible();
    const saved = await task(page.request, id);
    expect(saved.schedule).toMatchObject({ kind: "folder", folder: inbox, pattern: "*.pdf", input: "doc" });
    expect(saved.next_run_at).toBeNull();
    // Its runs may read the folder the files arrive in.
    expect(saved.permissions.folders).toContain(inbox);
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
    rmSync(inbox, { recursive: true, force: true });
  }
});
