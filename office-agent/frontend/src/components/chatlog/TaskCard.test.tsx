import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ProgressItem, ProgressStatus } from "../../lib/workflowProgress";
import { stepsInView, TaskCard } from "./TaskCard";

const list = (...statuses: ProgressStatus[]): ProgressItem[] => statuses.map((status, i) => ({ id: String(i + 1), content: `Step ${i + 1}`, status }));
const render = (tasks: ProgressItem[]) =>
  renderToStaticMarkup(<TaskCard entry={{ kind: "task_card", id: "c", tasks, done: false, bound: {} }} live />);

describe("the steps on the card", () => {
  it("strikes a finished step through, lifting the line while the pointer rests on it", () => {
    const html = render(list("completed", "in_progress"));
    expect(html).toMatch(/<span class="line-through group-hover\/step:no-underline">Step 1<\/span>/);
    expect(html).toMatch(/<span class="">Step 2<\/span>/);
  });

  it("shows a short list whole", () => {
    const html = render(list("completed", "in_progress", "pending"));
    expect(html).not.toContain("more</button>");
  });

  it("shows five steps of a long one and opens to the rest", () => {
    const html = render(list("completed", "completed", "completed", "completed", "in_progress", "pending", "pending", "pending"));
    expect(html.match(/Step \d/g)).toEqual(["Step 2", "Step 3", "Step 4", "Step 5", "Step 6"]);
    expect(html).toContain("Show 3 more</button>");
  });
});

describe("stepsInView", () => {
  const ids = (tasks: ProgressItem[]) => stepsInView(tasks).map((t) => t.id);

  it("keeps three finished steps above the first open one", () => {
    expect(ids(list("completed", "completed", "completed", "completed", "in_progress", "pending", "pending"))).toEqual(["2", "3", "4", "5", "6"]);
  });

  it("starts at the top while the first steps run", () => {
    expect(ids(list("in_progress", "pending", "pending", "pending", "pending", "pending"))).toEqual(["1", "2", "3", "4", "5"]);
  });

  it("ends at the bottom once only the last steps are open", () => {
    expect(ids(list("completed", "completed", "completed", "completed", "completed", "in_progress"))).toEqual(["2", "3", "4", "5", "6"]);
  });
});
