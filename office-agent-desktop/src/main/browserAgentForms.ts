/**
 * Filling a form, several actions on one page in one step, and waiting for
 * the first of several texts. The single actions stay in browserAgent.ts and
 * come in as `PageActions`, so this file adds no import cycle.
 */

import type { WebContents } from "electron";
import type { Command } from "./browserAgent";
import { fillBatch } from "./browserAgentBatch";
import { locate, splitRef } from "./browserAgentLocate";
import type { PageDialog, TabCdp } from "./browserCdp";
import type { Tab } from "./browserPanel";

export interface FormField { ref: string; text: string }
export type PageStep = Record<string, unknown>;

export interface PageActions {
  act(command: Command, tab: Tab, wc: WebContents, cdp: TabCdp, args: Record<string, unknown>): Promise<Record<string, unknown>>;
  resolveTarget(cdp: TabCdp, target: string, waitS?: number): Promise<string>;
  settle(wc: WebContents, timeoutMs?: number): Promise<void>;
  click(wc: WebContents, cdp: TabCdp, point: { x: number; y: number }, clickCount: number): Promise<void>;
  checkStop(): void;
  describeDialog(dialog: PageDialog): string;
}

interface FieldState { kind: string; checked: boolean; value: string }

const CHECKED_WORDS = /^(checked|check|yes|true|on|1|选中|是)$/i;
const UNCHECKED_WORDS = /^(unchecked|uncheck|no|false|off|0|不选|否)$/i;

/** Run in the page like pageAgent (browserAgentPage.ts), so self-contained:
 * it reaches pageAgent's elements only through the refs it left on window. */
export function pageFields(action: string, args: Record<string, unknown>): unknown {
  const w = window as unknown as { __coscribeAgent?: { refs: Map<string, WeakRef<Element>> } };
  if (action === "has_any_text") {
    const page = document.body?.innerText ?? "";
    return { found: (args.texts as string[]).find((text) => page.includes(text)) ?? null };
  }
  const el = w.__coscribeAgent?.refs.get(String(args.ref))?.deref();
  if (!el?.isConnected) throw new Error(`No element with ref ${args.ref} on this page any more -- take a new browser_snapshot.`);
  if (action === "set_value") {
    if (!(el instanceof HTMLInputElement)) throw new Error(`${args.element} isn't a field with a fixed format.`);
    const wanted = String(args.value);
    // The prototype's setter, so frameworks that track the value see the change.
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(el, wanted);
    if (el.value !== wanted) {
      const formats: Record<string, string> = { date: "2026-11-16", time: "14:30", "datetime-local": "2026-11-16T14:30", month: "2026-11", week: "2026-W47", color: "#1a2b3c" };
      throw new Error(`${args.element} doesn't take "${wanted}"; give it like ${formats[el.type] ?? "a number in its range"}.`);
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return {};
  }
  const role = el.getAttribute("role");
  const type = el instanceof HTMLInputElement ? el.type : "";
  let kind = "text";
  if (el instanceof HTMLSelectElement) kind = "select";
  else if (type === "checkbox" || role === "checkbox" || role === "switch") kind = "checkbox";
  else if (type === "radio" || role === "radio") kind = "radio";
  // Chromium's own pickers take no typed text, only a value in their fixed format.
  else if (["date", "time", "datetime-local", "month", "week", "color", "range"].includes(type)) kind = "picker";
  const checked = el instanceof HTMLInputElement && (type === "checkbox" || type === "radio")
    ? el.checked : el.getAttribute("aria-checked") === "true";
  const value = el instanceof HTMLSelectElement
    ? Array.from(el.selectedOptions).map((o) => o.text.trim()).join(", ")
    : el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement ? el.value : (el.textContent ?? "").trim();
  return { kind, checked, value };
}

/** Every kind of field in one call, each read back afterwards: a page may
 * reformat what it was given, and the result says so rather than hiding it. */
export async function fillForm(page: PageActions, command: Command, tab: Tab, wc: WebContents, cdp: TabCdp, fields: FormField[], waitS: number): Promise<Record<string, unknown>[]> {
  const mode = command.args.mode ?? "batch";
  if (mode === "batch") return fillBatch(page, wc, cdp, fields, waitS);
  if (mode !== "type") throw new Error('Use mode="batch" or mode="type".');
  const filled: Record<string, unknown>[] = [];
  for (const field of fields) {
    page.checkStop();
    const ref = await page.resolveTarget(cdp, field.ref, waitS);
    const text = String(field.text ?? "");
    const { key, inner } = splitRef(ref);
    const frame = cdp.frame(key);
    const point = await locate(cdp, ref);
    const before = await cdp.agent<FieldState>(frame, "field_state", { ref: inner }, pageFields);
    let want: boolean | undefined;
    let expected = text.trim();
    if (before.kind === "checkbox") {
      if (!CHECKED_WORDS.test(expected) && !UNCHECKED_WORDS.test(expected)) {
        throw new Error(`${point.element} is a checkbox: give "checked" or "unchecked", not "${text}".`);
      }
      want = CHECKED_WORDS.test(expected);
    } else if (before.kind === "radio") want = true;
    if (want !== undefined) {
      if (before.checked !== want) await page.click(wc, cdp, point, 1);
    } else if (before.kind === "select") {
      const { selected } = await cdp.agent<{ selected: string[] }>(frame, "select_option", { ref: inner, values: [text] });
      expected = selected.join(", ");
    } else if (before.kind === "picker") {
      await cdp.agent(frame, "set_value", { ref: inner, value: text, element: point.element }, pageFields);
    } else {
      await page.act({ ...command, action: "type" }, tab, wc, cdp, { ref, text, submit: false });
    }
    // Text input already settles in act; other controls still need their change to land.
    if (before.kind !== "text") await page.settle(wc);
    const after = await cdp.agent<FieldState>(frame, "field_state", { ref: inner }, pageFields).catch(() => null);
    const value = !after ? null : want !== undefined ? (after.checked ? "checked" : "unchecked") : after.value;
    const kept = value === null || (want !== undefined ? after?.checked === want : value.trim() === expected);
    filled.push({ ref: field.ref, element: point.element, value, changed: !kept });
  }
  return filled;
}

/** Several actions on one page in order, stopping at the first that fails. */
export async function runSteps(page: PageActions, command: Command, tab: Tab, wc: WebContents, cdp: TabCdp, steps: PageStep[], waitS: number): Promise<Record<string, unknown>> {
  const done: string[] = [];
  for (const [index, step] of steps.entries()) {
    page.checkStop();
    const [kind] = Object.keys(step).filter((k) => ["click", "type", "select", "press_key", "wait_for", "fill"].includes(k));
    try {
      if (kind === "fill") {
        await fillForm(page, { ...command, args: { ...command.args, mode: step.mode ?? "batch" } }, tab, wc, cdp, step.fill as FormField[], waitS);
      } else if (kind === "press_key") {
        await page.act({ ...command, action: "press_key" }, tab, wc, cdp, { key: step.press_key });
      } else if (kind === "wait_for") {
        await page.act({ ...command, action: "wait_for" }, tab, wc, cdp, { text: step.wait_for, timeout: waitS });
      } else if (kind) {
        const ref = await page.resolveTarget(cdp, String(step[kind]), waitS);
        const action = kind === "select" ? "select_option" : kind;
        const values = kind === "select" ? (Array.isArray(step.values) ? step.values : [step.values]).map(String) : undefined;
        await page.act({ ...command, action }, tab, wc, cdp, { ref, text: step.text, submit: step.submit, values });
      } else throw new Error("it names no action");
      done.push(`${kind} ${String(kind === "fill" ? `${(step.fill as unknown[]).length} fields` : step[kind])}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`Step ${index + 1} of ${steps.length} (${kind ?? "?"}) failed: ${message}${done.length ? ` Done before it: ${done.join("; ")}.` : ""}`);
    }
  }
  return { done };
}

/** Until one of the texts is on the page; which one comes back. */
export async function waitForAny(page: PageActions, cdp: TabCdp, texts: string[], waitS: number): Promise<Record<string, unknown>> {
  const deadline = Date.now() + waitS * 1000;
  for (;;) {
    page.checkStop();
    const { found } = await cdp
      .agent<{ found: string | null }>(cdp.main, "has_any_text", { texts }, pageFields)
      .catch(() => ({ found: null }));
    if (found !== null) return { found_text: found };
    if (cdp.dialog) throw new Error(page.describeDialog(cdp.dialog));
    if (Date.now() >= deadline) throw new Error(`None of ${texts.map((t) => `"${t}"`).join(", ")} appeared after ${waitS}s.`);
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}
