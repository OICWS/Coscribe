import { expect, test } from "@playwright/test";
import { pickOption } from "./helpers";

// A task set to start when a program on the machine sends it an event (decision 0040): the form
// turns it on, the task page shows its address and key, a sample's fields fill the inputs, and an
// event sent the way a script would send one starts a run, or is refused with the reason.

test("a workflow task starts on an event a program sends it", async ({ page }) => {
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e webhook",
      kind: "manual",
      at: "",
      approval_mode: "auto",
      workflow: {
        inputs: [
          { name: "amount", label: "Amount", type: "number" },
          { name: "customer", label: "Customer", type: "text" },
        ],
        steps: [
          {
            id: "write",
            kind: "tool",
            title: "Write it down",
            tool: "write_file",
            args: { path: "e2e-webhook.txt", content: "{{customer}}: {{amount}}" },
          },
        ],
      },
    },
  });
  const id = (await created.json()).trigger_id;
  try {
    await page.goto(`/?view=scheduled&task=${id}`);
    await page.getByRole("button", { name: "Edit" }).first().click();
    await pickOption(page.getByLabel("Frequency"), "When a program sends it an event");
    await expect(page.getByText("Save the task to get its address and key.")).toBeVisible();
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(page.getByText("When a program on this computer sends it an event").first()).toBeVisible();
    const address = page.getByTestId("webhook-address");
    await expect(address).toBeVisible();
    const url = (await address.getByTestId("webhook-url").textContent()) ?? "";
    expect(url).toMatch(new RegExp(`^http://127\\.0\\.0\\.1:\\d+/hooks/${id}$`));
    await expect(address.getByTestId("webhook-key")).not.toContainText(/[A-Za-z0-9]{20}/);
    await address.getByRole("button", { name: "Show" }).click();
    const key = (await address.getByTestId("webhook-key").textContent()) ?? "";
    expect(key.length).toBeGreaterThan(30);
    const send = (data: unknown, withKey = key) =>
      page.request.post(url, { headers: { Authorization: `Bearer ${withKey}` }, data });

    // The next event is kept as a sample, and starts no run.
    await page.getByTestId("webhook-sample").click();
    await expect(address).toContainText("Waiting: the next event is kept here");
    expect((await send({ total: 12.5, id: "inv-1", customer: { name: "Ada" } })).status()).toBe(200);
    await expect(address).toContainText("Sample kept: 3 fields", { timeout: 10_000 });

    await page.getByRole("button", { name: "Edit" }).first().click();
    // The form shows the address too, with the sample's fields to pick from.
    await expect(page.getByTestId("webhook-address")).toHaveCount(2);
    await pickOption(page.getByLabel("Amount from"), "total · 12.5");
    await pickOption(page.getByLabel("Customer from"), "customer.name · Ada");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByText("the event's customer.name")).toBeVisible();

    expect((await send({ total: 3 }, "wrong")).status()).toBe(401);
    const refused = await send({ total: "soon", customer: { name: "Bo" } });
    expect(refused.status()).toBe(400);
    expect((await refused.json()).error).toContain("Amount needs a number");
    const started = await send({ total: 40, customer: { name: "Cy" } });
    expect(started.status(), await started.text()).toBe(202);

    await expect(page.getByTestId("webhook-note")).toContainText("didn't run: Amount needs a number", {
      timeout: 15_000,
    });
    await expect(page.getByText("· Webhook").first()).toBeVisible({ timeout: 15_000 });
    const tasks = await (await page.request.get("/api/scheduled-tasks")).json();
    const saved = tasks.find((t: { trigger_id: string }) => t.trigger_id === id);
    expect(saved.schedule).toMatchObject({
      kind: "webhook",
      inputs_from: { amount: "total", customer: "customer.name" },
      per_hour: 30,
    });
    const run = saved.runs.find((r: { source: string }) => r.source === "webhook");
    expect(run.inputs).toEqual({ amount: 40, customer: "Cy" });
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${id}`);
  }
});
