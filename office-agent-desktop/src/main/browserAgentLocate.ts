/**
 * Where the AI's input lands on a page: the spot in the tab's viewport for
 * an element it named (through the iframes it sits in), and the area a
 * scroll moves. browserAgent.ts sends the real input there.
 */

import type { AgentFrame, TabCdp } from "./browserCdp";
import { pageScroll } from "./browserAgentPage";

// A banner sliding away or a dialog closing after the last step.
const COVERED_WAIT_MS = 2000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** "f2e7" -> frame "f2", element "e7"; "e7" is in the page itself. */
export function splitRef(ref: unknown): { key: string; inner: string } {
  const text = String(ref ?? "").trim();
  const match = /^(f\d+)(e\d+)$/.exec(text);
  return match ? { key: match[1], inner: match[2] } : { key: "", inner: text };
}

/** Where `point`, in `frame`'s own viewport, is in the tab's: plus the
 * offset of each iframe it sits in. */
async function inTab(cdp: TabCdp, frame: AgentFrame, point: { x: number; y: number; element: string }): Promise<{ x: number; y: number }> {
  let { x, y } = point;
  let bounds: { width: number; height: number } | null = null;
  for (let f: AgentFrame = frame; f.parent; f = f.parent) {
    const box = await cdp.agent<{ x: number; y: number; width: number; height: number }>(f.parent, "frame_box", { index: f.index });
    x += box.x;
    y += box.y;
    bounds = box;
  }
  if (bounds && (x < 0 || y < 0 || x > bounds.width || y > bounds.height)) {
    throw new Error(`${point.element} is outside the visible part of its frame -- scroll it into view first.`);
  }
  return { x, y };
}

/** Where to click element `ref`, in the tab's viewport. Something laid
 * over it (a banner, a dialog's backdrop) would take the click instead:
 * given a moment to go, it fails the step with what it is. */
export async function locate(cdp: TabCdp, ref: unknown, overlaid = false): Promise<{ x: number; y: number; element: string; frame: AgentFrame; inner: string }> {
  const { key, inner } = splitRef(ref);
  const frame = cdp.frame(key);
  type Point = { x: number; y: number; element: string; outside: boolean; right: number; covered: string };
  let point = await cdp.agent<Point>(frame, "locate", { ref: inner });
  // Past the right edge even at the AI's width: a toolbar wider still.
  if (point.outside && point.right > 0 && (await cdp.widenTo(point.right))) point = await cdp.agent<Point>(frame, "locate", { ref: inner });
  for (const deadline = Date.now() + COVERED_WAIT_MS; point.covered && !overlaid && Date.now() < deadline; ) {
    await sleep(200);
    point = await cdp.agent<Point>(frame, "locate", { ref: inner });
  }
  if (point.outside) throw new Error(`${point.element} is cut off outside the visible part of the page, so it can't be clicked.`);
  if (point.covered && !overlaid) {
    throw new Error(`${point.element} is covered by ${point.covered}, which would take the click -- close or answer that first.`);
  }
  return { ...(await inTab(cdp, frame, point)), element: point.element, frame, inner };
}

/** Turns the wheel over the area to scroll -- the one `within` sits in, or
 * the one under the middle of the view -- and says whether it moved. */
export async function scrollArea(cdp: TabCdp, direction: string, within: unknown): Promise<Record<string, unknown>> {
  if (!["up", "down", "left", "right"].includes(direction)) throw new Error('direction must be "up", "down", "left" or "right".');
  const { key, inner } = within ? splitRef(within) : { key: "", inner: undefined };
  const frame = cdp.frame(key);
  type Probe = { x: number; y: number; step: number; area: string; native: boolean; sig: string };
  const probe = await cdp.agent<Probe>(frame, "probe", { direction, within: inner }, pageScroll);
  const sign = direction === "up" || direction === "left" ? -1 : 1;
  const sideways = direction === "left" || direction === "right";
  let after: { progress: string; sig: string };
  if (probe.native) {
    after = await cdp.agent(frame, "nudge", { direction, step: sign * probe.step }, pageScroll);
  } else {
    const { x, y } = await inTab(cdp, frame, { ...probe, element: probe.area });
    await cdp.input("Input.dispatchMouseEvent", { type: "mouseWheel", x, y, deltaX: sideways ? sign * probe.step : 0, deltaY: sideways ? 0 : sign * probe.step });
    await sleep(250);
    after = await cdp.agent(frame, "measure", { direction }, pageScroll);
  }
  if (after.sig === probe.sig) {
    return { note: `Nothing moved: ${probe.area} is already at its end, or doesn't scroll ${direction}. To scroll a list or table that isn't in the middle of the view, pass within= the ref of something inside it.` };
  }
  return { note: `Scrolled ${probe.area} ${direction}${after.progress ? `; now ${after.progress}` : ""}.` };
}
