import { describe, expect, it } from "vitest";
import {
  applyDrop,
  arrangeAll,
  arrangementLayout,
  arrangementPanels,
  dropAt,
  hintFor,
  isArrangement,
  movePanel,
  openPanel,
  withoutPanel,
  type Arrangement,
} from "./dockArrangement";
import type { DockNode } from "./dockLayout";

const panel = (id: "task" | "browser" | "background"): DockNode => ({ kind: "panel", id });
const AREA = { x: 0, y: 0, w: 1400, h: 800 };

/** Task details on the left; Background tasks over Browser on the right. */
const both: Arrangement = {
  left: [{ tree: panel("task"), width: 300 }],
  right: [
    {
      tree: { kind: "split", dir: "col", sizes: [0.5, 0.5], children: [panel("background"), panel("browser")] },
      width: 400,
    },
  ],
};

describe("arrangementLayout", () => {
  it("gives the conversation what the columns leave, between them", () => {
    const placed = arrangementLayout(both, AREA, 380);
    expect(placed.panels.task).toEqual({ x: 8, y: 8, w: 300, h: 784 });
    expect(placed.chat).toEqual({ x: 316, y: 0, w: 668, h: 800 });
    expect(placed.panels.background).toMatchObject({ x: 992, w: 400 });
    expect(placed.overlay).toBe(false);
  });

  it("narrows the columns before the conversation goes below its minimum", () => {
    const placed = arrangementLayout(both, { ...AREA, w: 1000 }, 380);
    expect(placed.chat.w).toBeGreaterThanOrEqual(380);
    expect(placed.panels.task?.w).toBeLessThan(300);
  });

  it("lays the panels over the conversation when even narrow columns don't fit", () => {
    const placed = arrangementLayout(both, { ...AREA, w: 800 }, 380);
    expect(placed.overlay).toBe(true);
    expect(placed.chat).toEqual({ ...AREA, w: 800 });
    expect(placed.panels.browser?.w).toBe(280);
  });
});

describe("dropAt and applyDrop", () => {
  const placed = arrangementLayout(both, AREA, 380);

  it("over the conversation's left half, makes a column left of it", () => {
    const drop = dropAt(placed, both, AREA, "browser", 400, 400);
    expect(drop).toEqual({ kind: "column", side: "left", index: 1 });
    const next = applyDrop(both, "browser", drop!, 400);
    expect(next.left.map((c) => arrangementPanels({ left: [c], right: [] }))).toEqual([["task"], ["browser"]]);
    expect(arrangementPanels({ left: [], right: next.right })).toEqual(["background"]);
  });

  it("over a panel, goes beside it on its nearest edge", () => {
    const drop = dropAt(placed, both, AREA, "browser", 150, 780);
    expect(drop).toEqual({ kind: "beside", target: "task", edge: "bottom" });
    expect(applyDrop(both, "browser", drop!, 400).left[0].tree).toMatchObject({ dir: "col" });
  });

  it("near the window's edge, makes the outermost column", () => {
    expect(dropAt(placed, both, AREA, "task", 1395, 400)).toEqual({ kind: "column", side: "right", index: 1 });
  });

  it("moving a panel alone in its column to the other side keeps the column count right", () => {
    const next = applyDrop(both, "task", { kind: "column", side: "right", index: 1 }, 300);
    expect(next.left).toEqual([]);
    expect(next.right).toHaveLength(2);
    expect(arrangementPanels(next)).toEqual(["background", "browser", "task"]);
  });
});

describe("the Move menu and arrange", () => {
  it("moves to the far left as a new column", () => {
    const next = movePanel(both, "background", "left", 400);
    expect(arrangementPanels({ left: next.left, right: [] })).toEqual(["background", "task"]);
  });

  it("stacks a lone panel on the nearest other column", () => {
    const next = movePanel(both, "task", "top", 300);
    expect(next.left).toEqual([]);
    expect(arrangementPanels(next)).toEqual(["task", "background", "browser"]);
  });

  it("arranges every panel side by side on the right", () => {
    expect(arrangeAll(both, "row").right).toHaveLength(3);
    expect(arrangeAll(both, "col").right).toHaveLength(1);
  });
});

describe("closing and opening", () => {
  it("puts a closed panel back beside its neighbour, or as its own column", () => {
    const hint = hintFor(both, "browser");
    expect(hint).toEqual({ target: "background", edge: "bottom" });
    const back = openPanel(withoutPanel(both, "browser"), "browser", hint!, 440, 0);
    expect(back).toEqual(both);
    const taskHint = hintFor(both, "task");
    expect(taskHint).toEqual({ side: "left", index: 0, width: 300 });
    expect(openPanel(withoutPanel(both, "task"), "task", taskHint!, 320, 0)).toEqual(both);
  });

  it("opens a new panel as a column while there is room, else under the rightmost panel", () => {
    const one: Arrangement = { left: [], right: [{ tree: panel("task"), width: 320 }] };
    expect(openPanel(one, "browser", undefined, 440, 500).right).toHaveLength(2);
    const stacked = openPanel(one, "browser", undefined, 440, 100);
    expect(stacked.right).toHaveLength(1);
    expect(stacked.right[0].tree).toMatchObject({ dir: "col" });
  });

  it("accepts only a well-formed saved arrangement", () => {
    expect(isArrangement(both)).toBe(true);
    expect(isArrangement({ left: [], right: [{ tree: panel("task"), width: -1 }] })).toBe(false);
    expect(isArrangement({ tree: panel("task"), width: 300 })).toBe(false);
  });
});
