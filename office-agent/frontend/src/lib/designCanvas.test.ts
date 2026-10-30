import { describe, expect, it } from "vitest";
import { fitView, zoomAt, type Canvas } from "./designCanvas";

const board = (id: string, x: number, y: number, width: number, height: number) => ({ id, title: id, file: `${id}.html`, path: `${id}.html`, x, y, width, height });

describe("the canvas view", () => {
  it("zooms around the pointer, which stays over the same canvas point", () => {
    const view = { x: 100, y: 50, zoom: 1 };
    const zoomed = zoomAt(view, 2, 200, 100);
    expect(zoomed.zoom).toBe(2);
    expect(zoomed.x + 200 / zoomed.zoom).toBe(view.x + 200 / view.zoom);
    expect(zoomed.y + 100 / zoomed.zoom).toBe(view.y + 100 / view.zoom);
  });

  it("does not zoom past its limits", () => {
    expect(zoomAt({ x: 0, y: 0, zoom: 3 }, 10, 0, 0).zoom).toBe(4);
    expect(zoomAt({ x: 0, y: 0, zoom: 0.1 }, 0.01, 0, 0).zoom).toBe(0.05);
  });

  it("fits every board in the panel, centred, and never enlarges past 100%", () => {
    const canvas: Canvas = { boards: [board("a", 0, 0, 1280, 800), board("b", 1360, 0, 1280, 800)], notes: [] };
    const view = fitView(canvas, 1000, 600);
    expect(view.zoom).toBeCloseTo((1000 - 96) / 2640);
    const small = fitView({ boards: [board("a", 0, 0, 200, 100)], notes: [] }, 1000, 600);
    expect(small.zoom).toBe(1);
    expect(small.x + 1000 / 2).toBeCloseTo(100);
  });
});
