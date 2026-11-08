import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { pickOption } from "./helpers";

// A task set to start when something new shows up in a connector (decision 0039), against a real
// MCP server (fixtures/inbox_mcp.py) the server starts: the form asks its tool once and fills the
// inputs from what it found. The checks the scheduler makes are tested in pytest, since they need
// a task to come due.

const FIXTURE = resolve(dirname(fileURLToPath(import.meta.url)), "fixtures", "inbox_mcp.py");

test("a workflow task can start on each new item in a connector", async ({ page }) => {
  // Adding and removing a connector rebuilds every open conversation's agent, and late in the
  // suite there are dozens: each takes about 50 s on CI's runner, on main as on this branch.
  test.setTimeout(150_000);
  const dir = mkdtempSync(join(tmpdir(), "coscribe-e2e-inbox-"));
  const inbox = join(dir, "inbox.json");
  writeFileSync(
    inbox,
    JSON.stringify([
      { id: "m1", subject: "Invoice 1041", amount: 120, from: { email: "billing@acme.example" }, labels: ["invoices"] },
      { id: "m2", subject: "Lunch on Friday?", amount: 0, from: { email: "sam@acme.example" }, labels: [] },
    ]),
  );
  const added = await page.request.post("/api/mcp/servers", {
    data: {
      name: "inbox",
      command: process.env.COSCRIBE_E2E_PYTHON ?? "python",
      args: [FIXTURE],
      env: { INBOX_FILE: inbox },
    },
  });
  expect(added.ok(), await added.text()).toBeTruthy();
  await expect
    .poll(
      async () => (await (await page.request.get("/api/tools")).json()).tools.map((t: { name: string }) => t.name),
      {
        timeout: 30_000,
      },
    )
    .toContain("inbox_search_messages");
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e invoices",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [
          { name: "amount", label: "Amount", type: "number" },
          { name: "sender", label: "Sent by", type: "text" },
        ],
        steps: [{ id: "list", kind: "tool", title: "List what is there", tool: "list_files", args: {} }],
      },
    },
  });
  const id = (await created.json()).trigger_id;
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    await page.getByRole("button", { name: "Edit" }).first().click();
    await pickOption(page.getByLabel("Frequency"), "When something new shows up in a connector");

    // A tool that may change things is asked only once the person says it only reads.
    await pickOption(page.getByLabel("Tool to ask"), "Archive message (may change things)");
    const checkNow = page.getByRole("button", { name: "Check now" });
    await expect(checkNow).toBeDisabled();
    await expect(page.getByText("It only reads: ask it every few minutes.")).toBeVisible();

    await pickOption(page.getByLabel("Tool to ask"), "Search messages");
    await page.getByLabel("label").fill("invoices");
    await checkNow.click();
    await expect(page.getByText("It has 1 item now:")).toBeVisible();
    await expect(page.getByText("Invoice 1041")).toBeVisible();
    // "amount" is named like its input; "Sent by" is picked.
    await expect(page.getByLabel("Amount from")).toContainText("amount · 120");
    await pickOption(page.getByLabel("Sent by from"), "from.email · billing@acme.example");
    await page.getByRole("button", { name: "Save" }).click();

    await expect(
      page.getByText("When Inbox has something new (invoices) · checks every 30 minutes").first(),
    ).toBeVisible();
    await expect(page.getByText("the new item's from.email")).toBeVisible();
    await expect(page.getByTestId("connector-check")).toContainText("Not checked yet");
    const tasks = await (await page.request.get("/api/scheduled-tasks")).json();
    const saved = tasks.find((t: { trigger_id: string }) => t.trigger_id === id);
    expect(saved.schedule).toMatchObject({
      kind: "connector",
      tool: "inbox_search_messages",
      args: { label: "invoices" },
      inputs_from: { amount: "amount", sender: "from.email" },
      minutes: 30,
      per_hour: 30,
      trust_unmarked: false,
    });
    expect(saved.next_run_at).toBeTruthy();
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
    await page.request.delete("/api/mcp/servers/inbox");
    rmSync(dir, { recursive: true, force: true });
  }
});
