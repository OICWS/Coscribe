import type { Box } from "./slideSource";

export type Point = [number, number];

/** A line's two ends, left one first, as its box and whether it rises to the right say. */
export function lineEnds([x, y, w, h]: Box, rises: boolean): [Point, Point] {
  return rises ? [[x, y + h], [x + w, y]] : [[x, y], [x + w, y + h]];
}

/** The box and direction of the line between two points, whichever is on the left. */
export function lineBetween(a: Point, b: Point): { box: Box; rises: boolean } {
  const [left, right] = a[0] <= b[0] ? [a, b] : [b, a];
  return {
    box: [left[0], Math.min(a[1], b[1]), right[0] - left[0], Math.abs(a[1] - b[1])],
    rises: right[1] < left[1],
  };
}
