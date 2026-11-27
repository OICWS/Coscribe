import { describe, expect, it } from "vitest";
import type { ConversationActivity } from "../../lib/transcriptGrouping";
import { DEPARTED, GATHER, poseAt } from "./activityRobotMotion";

const rest = [0, 0, 0, 1, 1];

const gestures: Record<ConversationActivity, number> = {
  Thinking: 1.40,
  "Running commands": 1.27,
  Reading: 1.78,
  Writing: 1.78,
  Editing: 1.85,
  Searching: 2.25,
  Browsing: 2.63,
  Working: 2.31,
};

describe("activity robot poses", () => {
  it.each(Object.entries(gestures) as [ConversationActivity, number][])(
    "%s leaves its neutral pose and returns before the dots come back",
    (activity, peak) => {
      // Include the shortest and longest pose timing offsets.
      for (const start of [0, 5.89 / 4, 3 * 5.89 / 4]) {
        const still = (phase: number) => {
          poseAt(activity, phase, start + phase).forEach((axis, index) => {
            expect(axis).toBeCloseTo(rest[index], 6);
          });
        };
        still(GATHER);
        expect(poseAt(activity, peak, start + peak).some((axis, index) => Math.abs(axis - rest[index]) > 0.1)).toBe(true);
        still(DEPARTED - 0.04);
      }
    },
  );

  it("searches in one sweep from lower left to lower right across entrances", () => {
    const phases = [1.35, 1.62, 1.94, 2.24, 2.57];
    for (const entrance of [0, 5.5, 11]) {
      const poses = phases.map((phase) => poseAt("Searching", phase, entrance + phase));
      expect(poses[0][0]).toBeLessThan(-0.25);
      expect(poses[poses.length - 1][0]).toBeGreaterThan(0.25);
      expect(poses.map(([yaw]) => yaw)).toEqual(poses.map(([yaw]) => yaw).sort((a, b) => a - b));
      for (const [yaw, pitch, , height, width] of poses) {
        expect(Math.abs(yaw)).toBeLessThan(0.5);
        expect(pitch).toBeCloseTo(0.31);
        expect([height, width]).toEqual([1, 1]);
      }
    }
  });
});
