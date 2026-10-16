import { describe, expect, it } from "vitest";
import {
  arrange,
  columnCount,
  dragGutter,
  dropTarget,
  edgeOf,
  insertPanel,
  isDockNode,
  layout,
  neighbourOf,
  panelIds,
  placeNewPanel,
  removePanel,
  type DockNode,
} from "./dockLayout";

const panel = (id: "task" | "browser" | "background"): DockNode => ({ kind: "panel", id });
const AREA = { x: 0, y: 0, w: 808, h: 600 };

/** Two columns: Background tasks over Task details, then Browser. */
const twoColumns: DockNode = {
  kind: "split",
  dir: "row",
  sizes: [0.5, 0.5],
  children: [{ kind: "split", dir: "col", sizes: [0.5, 0.5], children: [panel("background"), panel("task")] }, panel("browser")],
};

describe("insertPanel", () => {
  it("puts a panel beside another and splits that one's share", () => {
    const tree = insertPanel(panel("task"), "browser", "task", "bottom");
    expect(tree).toEqual({ kind: "split", dir: "col", sizes: [0.5, 0.5], children: [panel("task"), panel("browser")] });
  });

  it("moves a panel already in the tree instead of copying it", () => {
    const tree = insertPanel(twoColumns, "task", "browser", "top");
    expect(panelIds(tree).sort()).toEqual(["background", "browser", "task"]);
    expect(columnCount(tree)).toBe(2);
    const right = tree.kind === "split" ? tree.children[1] : null;
    expect(right).toEqual({ kind: "split", dir: "col", sizes: [0.5, 0.5], children: [panel("task"), panel("browser")] });
  });

  it("along an edge of everything, takes a share of the whole length", () => {
    const tree = insertPanel(twoColumns, "task", null, "left");
    expect(tree.kind === "split" && tree.dir).toBe("row");
    expect(panelIds(tree)).toEqual(["task", "background", "browser"]);
    expect(tree.kind === "split" && tree.sizes.reduce((a, b) => a + b)).toBeCloseTo(1);
  });

  it("along a cross edge of everything, wraps the rest", () => {
    const tree = insertPanel(twoColumns, "task", null, "bottom");
    expect(tree.kind === "split" && tree.dir).toBe("col");
    expect(panelIds(tree)).toEqual(["background", "browser", "task"]);
  });
});

describe("removePanel", () => {
  it("lifts a lone sibling and gives it the room", () => {
    const tree = removePanel(twoColumns, "task");
    expect(tree).toEqual({ kind: "split", dir: "row", sizes: [0.5, 0.5], children: [panel("background"), panel("browser")] });
  });

  it("leaves nothing when the last panel goes", () => {
    expect(removePanel(panel("task"), "task")).toBeNull();
  });
});

describe("layout", () => {
  it("fills the area exactly, with a gap and a gutter between neighbours", () => {
    const { panels, gutters } = layout(twoColumns, AREA, 8);
    expect(panels.background).toEqual({ x: 0, y: 0, w: 400, h: 296 });
    expect(panels.task).toEqual({ x: 0, y: 304, w: 400, h: 296 });
    expect(panels.browser).toEqual({ x: 408, y: 0, w: 400, h: 600 });
    expect(gutters.map((g) => [g.dir, g.rect])).toEqual([
      ["col", { x: 0, y: 296, w: 400, h: 8 }],
      ["row", { x: 400, y: 0, w: 8, h: 600 }],
    ]);
  });

  it("names the area edge a panel spans", () => {
    const { panels } = layout(twoColumns, AREA, 8);
    expect(edgeOf(panels, AREA, "browser")).toBe("right");
    expect(edgeOf(panels, AREA, "task")).toBeNull();
  });
});

describe("dropTarget", () => {
  const { panels } = layout(twoColumns, AREA, 8);

  it("picks the nearest edge of the panel under the pointer", () => {
    expect(dropTarget(panels, AREA, "task", 600, 560)).toMatchObject({ target: "browser", edge: "bottom" });
    expect(dropTarget(panels, AREA, "task", 430, 300)).toMatchObject({ target: "browser", edge: "left" });
  });

  it("near the area's border, means that side of everything", () => {
    expect(dropTarget(panels, AREA, "browser", 10, 300)).toMatchObject({ target: null, edge: "left" });
  });

  it("finds nothing outside the area or with nothing else open", () => {
    expect(dropTarget(panels, AREA, "task", -100, 300)).toBeNull();
    expect(dropTarget({ task: AREA }, AREA, "task", 300, 300)).toBeNull();
  });
});

describe("placeNewPanel", () => {
  it("opens a new column while columns stay wide enough", () => {
    expect(columnCount(placeNewPanel(panel("task"), panel("task"), "browser", 800, 300))).toBe(2);
  });

  it("stacks under the rightmost column when they would get too narrow", () => {
    const tree = { kind: "split", dir: "row", sizes: [0.5, 0.5], children: [panel("task"), panel("background")] } as DockNode;
    const placed = placeNewPanel(tree, tree, "browser", 700, 300);
    expect(columnCount(placed)).toBe(2);
    expect(placed.kind === "split" && placed.children[1]).toEqual({
      kind: "split",
      dir: "col",
      sizes: [0.5, 0.5],
      children: [panel("background"), panel("browser")],
    });
  });
});

describe("neighbourOf", () => {
  it("remembers a closed panel's place by the panel beside it", () => {
    expect(neighbourOf(twoColumns, "task")).toEqual({ target: "background", edge: "bottom" });
    expect(neighbourOf(twoColumns, "background")).toEqual({ target: "task", edge: "top" });
    expect(neighbourOf(twoColumns, "browser")).toEqual({ target: "task", edge: "right" });
  });

  it("puts the panel back where it was", () => {
    const hint = neighbourOf(twoColumns, "browser");
    const back = hint && insertPanel(removePanel(twoColumns, "browser"), "browser", hint.target, hint.edge);
    expect(back && panelIds(back)).toEqual(["background", "task", "browser"]);
  });
});

describe("the rest", () => {
  it("arranges every panel in one row", () => {
    expect(arrange(twoColumns, "row")).toMatchObject({ dir: "row", sizes: [1 / 3, 1 / 3, 1 / 3] });
  });

  it("keeps both sides of a dragged gutter at least the minimum", () => {
    expect(dragGutter([0.5, 0.5], 1, -1000, 800, 200)).toEqual([0.25, 0.75]);
    expect(dragGutter([0.5, 0.5], 1, 80, 800, 200)).toEqual([0.6, 0.4]);
  });

  it("accepts only a well-formed saved tree", () => {
    expect(isDockNode(twoColumns)).toBe(true);
    expect(isDockNode({ kind: "panel", id: "files" })).toBe(false);
    expect(isDockNode({ kind: "split", dir: "row", sizes: [1], children: [] })).toBe(false);
  });
});
