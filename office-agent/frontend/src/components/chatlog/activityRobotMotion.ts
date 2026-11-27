import type { ConversationActivity } from "../../lib/transcriptGrouping";

type Pose = readonly [yaw: number, pitch: number, roll: number, eyeHeight: number, eyeWidth: number];
type Keyframe = readonly [at: number, ...Pose];

export const GATHER = 0.58;
export const DEPARTED = 3.28;

const REST: Pose = [0, 0, 0, 1, 1];
const GESTURES = {
  Thinking: [
    [1.40, 0, -0.15, 0.04, 1.53, 1.23],
    [1.88, 0, 0, -0.07, 1, 1],
    [2.07, 0, 0, -0.07, 0.12, 1],
    [2.22, 0, 0, -0.07, 1, 1],
    [2.58, 0.10, 0.10, -0.09, 0.66, 1.18],
  ],
  "Running commands": [
    [1.27, -0.85, 0.51, -0.10, 0.90, 1],
    [2.64, 0.92, 0.53, 0.08, 0.90, 1],
  ],
  Reading: [
    [1.78, 0.93, -0.69, 0.16, 1.13, 1.08],
    [2.65, 0.76, -0.58, 0.14, 1.08, 1.06],
  ],
  Writing: [
    [1.23, -0.43, 0.39, -0.06, 0.94, 1],
    [1.78, -0.08, 0.49, -0.03, 0.94, 1],
    [2.25, 0.25, 0.49, 0.03, 0.94, 1],
    [2.70, 0.57, 0.39, 0.07, 0.94, 1],
  ],
  Editing: [
    [1.32, 0.53, 0.11, 0.11, 0.94, 1],
    [1.85, -0.58, 0.28, -0.12, 0.68, 1.12],
    [2.10, -0.58, 0.28, -0.12, 0.68, 1.12],
    [2.35, 0.54, 0.08, 0.08, 1.23, 1],
  ],
  Searching: [
    [1.22, 0.72, -0.14, 0.13, 1.19, 1],
    [1.58, -0.80, -0.14, -0.13, 1.19, 1],
    [1.95, 0.62, -0.22, 0.10, 1.18, 1],
    [2.25, 0.70, -0.26, 0.13, 1.36, 1.10],
    [2.67, 0.70, -0.26, 0.13, 1.23, 1.05],
  ],
  Browsing: [
    [1.28, 0.11, -0.34, 0.02, 1.06, 1],
    [1.76, 0.11, -0.34, 0.02, 1.06, 1],
    [2.63, 0.04, 0.66, 0.06, 0.84, 1],
  ],
  Working: [
    [1.33, 0, 0.38, 0.06, 0.86, 1],
    [1.73, 0, -0.18, -0.05, 1.05, 1],
    [2.14, 0, 0.27, 0.04, 0.89, 1],
    [2.31, 0, 0.14, 0.03, 0.13, 1],
    [2.55, 0, 0, 0, 1, 1],
  ],
} satisfies Record<ConversationActivity, readonly Keyframe[]>;

export function smooth(from: number, to: number, time: number): number {
  const fraction = Math.max(0, Math.min(1, (time - from) / (to - from)));
  return fraction * fraction * (3 - 2 * fraction);
}

export function wave(time: number, period: number, offset = 0): number {
  return Math.sin(time * 2 * Math.PI / period + offset);
}

export function poseAt(activity: ConversationActivity, phase: number, time: number): Pose {
  const keyframes: readonly Keyframe[] = GESTURES[activity];
  const variation = wave(time - phase, 5.89);
  const moment = phase + 0.07 * variation;
  const afterIndex = keyframes.findIndex(([at]) => at > moment);
  const next = afterIndex === -1 ? keyframes.length : afterIndex;
  const before: Keyframe = keyframes[next - 1] ?? [0.95, ...REST];
  const after: Keyframe = keyframes[next] ?? [3.13, ...REST];
  const mix = smooth(before[0], after[0], moment);
  const envelope = smooth(0.88, 1.25, phase) * (1 - smooth(2.71, 3.15, phase));
  const direction = (activity === "Reading" || activity === "Searching") && wave(time - phase, 11.9, 1.7) < 0 ? -1 : 1;
  const blend = (axis: 1 | 2 | 3 | 4 | 5) => before[axis] + (after[axis] - before[axis]) * mix;

  return [
    direction * blend(1) + 0.06 * envelope * wave(time, 5.37),
    blend(2),
    direction * blend(3) + 0.035 * envelope * wave(time, 4.83),
    blend(4),
    blend(5),
  ];
}

const RADIUS = 19.7;
const eyeOutline = [Math.PI, 0].flatMap((start, half) =>
  Array.from({ length: 9 }, (_, index) => {
    const angle = start + index * Math.PI / 8;
    return [Math.cos(angle) * 0.096, (half === 0 ? -0.099 : 0.099) + Math.sin(angle) * 0.087];
  }),
);

export function eyeAt(side: number, [yaw, pitch, roll, height, width]: Pose) {
  const longitude = side * 0.285;
  const cosYaw = Math.cos(yaw);
  const sinYaw = Math.sin(yaw);
  const cosPitch = Math.cos(pitch);
  const sinPitch = Math.sin(pitch);
  const cosRoll = Math.cos(roll);
  const sinRoll = Math.sin(roll);
  const front = Math.cos(longitude + yaw) * cosPitch;

  // Project the eye's rounded outline onto the turning sphere, so the far eye narrows at its edge.
  const path = eyeOutline.map(([across, down], index) => {
    const u = longitude + across * width;
    const v = -0.025 + down * height;
    const x = Math.sin(u) * Math.cos(v);
    const y = Math.sin(v);
    const z = Math.cos(u) * Math.cos(v);
    const horizontal = x * cosYaw + z * sinYaw;
    const depth = z * cosYaw - x * sinYaw;
    const vertical = y * cosPitch + depth * sinPitch;
    const scale = RADIUS * (1 + 0.055 * (depth * cosPitch - y * sinPitch));
    const screenX = scale * (horizontal * cosRoll - vertical * sinRoll);
    const screenY = scale * (horizontal * sinRoll + vertical * cosRoll);
    return `${index === 0 ? "M" : "L"}${screenX.toFixed(2)} ${screenY.toFixed(2)}`;
  }).join(" ");
  return { path: path + " Z", opacity: smooth(0.025, 0.23, front) };
}
