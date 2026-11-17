import type { WebContents } from "electron";
import type { FormField, PageActions } from "./browserAgentForms";
import { splitRef } from "./browserAgentLocate";
import type { TabCdp } from "./browserCdp";

/** Runs in one isolated-world call: browser editing commands retain input/change behavior
 * while allowing all writes to finish before the page gets another rendering turn. */
function pageBatch(action: string, args: Record<string, unknown>): unknown {
  const state = (window as unknown as { __coscribeAgent?: { refs: Map<string, WeakRef<Element>> } }).__coscribeAgent;
  const fields = args.fields as Array<{ ref: string; source: string; text: string }>;
  const valueOf = (el: HTMLElement): string => {
    if (el instanceof HTMLInputElement && ["checkbox", "radio"].includes(el.type)) return el.checked ? "checked" : "unchecked";
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) return el.value;
    return el.isContentEditable ? el.innerText : el.textContent ?? "";
  };
  const prepared = fields.map(field => {
    const el = state?.refs.get(field.ref)?.deref();
    if (!(el instanceof HTMLElement) || !el.isConnected) throw new Error(`${field.source} changed; take a fresh snapshot.`);
    const input = el instanceof HTMLInputElement ? el : null;
    const select = el instanceof HTMLSelectElement ? el : null;
    const toggle = input && ["checkbox", "radio"].includes(input.type);
    const picker = input && ["date", "time", "datetime-local", "month", "week", "color", "range"].includes(input.type);
    const editable = el instanceof HTMLTextAreaElement || el.isContentEditable ||
      input && ["text", "search", "email", "url", "tel", "password", "number"].includes(input.type);
    let expected = field.text;
    if (toggle) {
      if (input.type === "checkbox" && !/^(checked|check|yes|true|on|1|选中|是|unchecked|uncheck|no|false|off|0|不选|否)$/i.test(expected))
        throw new Error(`${field.source} needs "checked" or "unchecked".`);
      expected = input.type === "radio" || /^(checked|check|yes|true|on|1|选中|是)$/i.test(expected) ? "checked" : "unchecked";
    }
    if (select) {
      const option = [...select.options].find(option => option.value === field.text || option.text.trim() === field.text) ??
        [...select.options].find(option => option.text.trim().toLowerCase() === field.text.trim().toLowerCase());
      if (!option || option.matches(":disabled")) throw new Error(`${field.source} has no enabled option "${field.text}".`);
      expected = option.value;
    }
    if (action === "apply") {
      if (el.matches(":disabled") || (input ?? (el instanceof HTMLTextAreaElement ? el : null))?.readOnly)
        throw new Error(`${field.source} is disabled or read-only.`);
      if (!el.getClientRects().length || !(toggle || picker || select || editable))
        throw new Error(`${field.source} cannot use batch editing; use mode="type".`);
      if (picker) {
        const probe = input.cloneNode(false) as HTMLInputElement;
        probe.value = expected;
        if (probe.value !== expected) throw new Error(`${field.source} does not accept "${expected}".`);
      }
    }
    return { el, field, expected, toggle, picker, select };
  });
  if (action === "apply") {
    let done = 0;
    try {
      for (const { el, field, expected, toggle, picker, select } of prepared) {
        if (!el.isConnected) throw new Error(`${field.source} was replaced during editing.`);
        el.focus({ preventScroll: true });
        if (!el.isConnected || (el.getRootNode() as Document | ShadowRoot).activeElement !== el) throw new Error(`${field.source} could not keep focus.`);
        if (toggle) {
          if (valueOf(el) !== expected) el.click();
        } else if (select || picker) {
          const prototype = select ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(el, expected);
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
          if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) el.select();
          else document.execCommand("selectAll");
          const edited = document.execCommand(field.text ? "insertText" : "delete", false, field.text);
          if (!edited && valueOf(el) !== field.text) throw new Error(`${field.source} rejected batch editing; use mode="type".`);
        }
        done++;
      }
      prepared.at(-1)?.el.blur();
    } catch (error) {
      throw new Error(`Batch stopped after ${done}/${prepared.length} fields: ${error instanceof Error ? error.message : String(error)} Check the page before retrying.`);
    }
  }
  return prepared.map(({ el, field, expected }) => ({ ref: field.source, element: field.source,
    value: valueOf(el), changed: valueOf(el).trim() !== expected.trim() }));
}

export async function fillBatch(page: PageActions, wc: WebContents, cdp: TabCdp, fields: FormField[], waitS: number): Promise<Record<string, unknown>[]> {
  const targets = await Promise.all(fields.map(async field => {
    page.checkStop();
    const ref = splitRef(await page.resolveTarget(cdp, field.ref, waitS));
    return { ...ref, source: field.ref, text: String(field.text ?? "") };
  }));
  const key = targets[0]?.key;
  if (key === undefined || targets.some(target => target.key !== key))
    throw new Error('Batch fields must share one frame; split the batch or use mode="type".');
  const frame = cdp.frame(key);
  const args = { fields: targets.map(target => ({ ref: target.inner, source: target.source, text: target.text })) };
  page.checkStop();
  await cdp.agent(frame, "apply", args, pageBatch);
  await page.settle(wc);
  page.checkStop();
  return cdp.agent<Record<string, unknown>[]>(frame, "read", args, pageBatch);
}
