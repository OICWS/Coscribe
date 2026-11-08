import { expect, test, type APIRequestContext } from "@playwright/test";
import { pickOption } from "./helpers";

// No model involved: from the simple view a person changes a step's fixed values and an input's
// usual value without the full editor (decision 0031), and many paths stack instead of running
// off the page.

async function savedWorkflow(request: APIRequestContext, id: string) {
  const tasks = await (await request.get("/api/scheduled-tasks")).json();
  return tasks.find((t: { trigger_id: string }) => t.trigger_id === id).workflow;
}

test("a step's values and an input's usual value change from the simple view", async ({ page }) => {
  const read = (id: string, path: string) => ({
    id,
    kind: "tool",
    title: `Fill the ${id} template`,
    tool: "read_file",
    args: { path },
    save_as: "text",
  });
  const created = await page.request.post("/api/scheduled-tasks", {
    data: {
      name: "e2e quick edit",
      kind: "manual",
      at: "",
      workflow: {
        inputs: [
          { name: "month", label: "Month to report on", type: "date", default: "last_month_start" },
          { name: "dept", label: "Department", type: "choice", options: ["Sales", "Finance", "Ops"], default: "Sales" },
        ],
        steps: [
          {
            id: "pick",
            kind: "choice",
            title: "Use the department's template",
            value: "dept",
            cases: [
              { is: "Sales", steps: [read("sales", "sales.md")] },
              { is: "Finance", steps: [read("finance", "finance.md")] },
              { is: "Marketing", steps: [read("marketing", "marketing.md")] },
            ],
            otherwise: [read("other", "other.md")],
          },
        ],
      },
    },
  });
  const task = await created.json();
  expect(task.trigger_id, JSON.stringify(task)).toBeTruthy();
  try {
    await page.goto(`/?view=scheduled&task=${task.trigger_id}`);
    const simple = page.getByTestId("task-simple-view");
    await expect(page.locator('[data-plain-step="pick"]')).toContainText("Depending on Department");
    await expect(simple).toContainText("usually First day of last month");

    await page.locator('[data-plain-step="pick"]').click();
    const sheet = page.getByRole("complementary", { name: "Change this step" });
    await expect(sheet.getByLabel("Path 2, when “Department” is")).toHaveValue("Finance");
    await sheet.getByLabel("Path 3, when “Department” is").fill("Ops");
    await sheet.getByRole("button", { name: "Save" }).click();
    await expect(sheet).toHaveCount(0);
    await expect
      .poll(async () => (await savedWorkflow(page.request, task.trigger_id)).steps[0].cases[2].is)
      .toBe("Ops");

    await simple.getByRole("button", { name: "Change" }).nth(1).click();
    const input = page.getByRole("complementary", { name: "Change what it asks for" });
    await pickOption(input.getByLabel("Usually"), "Finance");
    await input.getByRole("button", { name: "Save" }).click();
    await expect(input).toHaveCount(0);
    await expect(simple).toContainText("usually Finance");
    await expect
      .poll(async () => (await savedWorkflow(page.request, task.trigger_id)).inputs[1].default)
      .toBe("Finance");
  } finally {
    await page.request.delete(`/api/scheduled-tasks/${task.trigger_id}`);
  }
});
