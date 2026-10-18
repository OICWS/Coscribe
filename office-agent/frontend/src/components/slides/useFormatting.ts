import { PRESETS, elementsOf, hexColour, presetOf, retag, setStyle, styleOf, type Preset } from "../../lib/slideSource";
import type { Align, TextFormat } from "./SlideFormatBar";

type Change = (edit: (elements: Element[]) => void, redraw: boolean) => void;
const TEXT_TAGS = ["h1", "h2", "h3", "p", "ul", "ol"];
const HEADINGS = ["h1", "h2", "h3"];

/** What the format bar shows for element `at` and what its buttons do. While typing with words
 * selected, bold, italic, underline and colour apply to those words; otherwise every change is
 * to the whole element, after the typing is written back. */
export function useFormatting(
  doc: Document | null,
  at: number | null,
  typing: boolean,
  stopTyping: () => void,
  change: Change,
) {
  const el = doc && at !== null ? elementsOf(doc)[at] : null;
  const format = el && TEXT_TAGS.includes(el.localName) ? formatOf(el, typing) : null;
  const onWords = () => typing && !(document.getSelection()?.isCollapsed ?? true);

  const whole = (edit: (el: Element) => void) => {
    if (at === null) return;
    if (typing) stopTyping();
    change((els) => edit(els[at]), false);
  };
  return {
    format,
    actions: {
      preset: (preset: Preset) =>
        whole((target) => {
          const { tag, size } = PRESETS[preset];
          const next = target.localName === "ul" || target.localName === "ol" ? target : retag(target, tag);
          setStyle(next, "font-size", size === null ? null : `${size}px`);
          if (HEADINGS.includes(next.localName)) setStyle(next, "font-weight", null);
        }),
      colour: (colour: string) => {
        if (onWords()) return void document.execCommand("foreColor", false, colour);
        whole((target) => setStyle(target, "color", colour));
      },
      toggle: (what: "bold" | "italic" | "underline" | "list") => {
        if (what !== "list" && onWords()) return void document.execCommand(what);
        if (!format) return;
        whole((target) => toggled(target, what, format));
      },
      align: (align: Align) => whole((target) => setStyle(target, "text-align", align)),
    },
  };
}

function toggled(target: Element, what: "bold" | "italic" | "underline" | "list", format: TextFormat) {
  if (what === "bold") setStyle(target, "font-weight", format.bold ? "400" : "700");
  else if (what === "italic") setStyle(target, "font-style", format.italic ? "normal" : "italic");
  else if (what === "list") retag(target, format.list ? "p" : "ul");
  else underline(target, !format.underline);
}

/** Underlines all of the element's text, or takes its underline off; a list item by item. */
function underline(target: Element, on: boolean) {
  const holders = target.localName === "ul" || target.localName === "ol" ? Array.from(target.children) : [target];
  for (const holder of holders) {
    const only = holder.children.length === 1 && holder.firstElementChild?.localName === "u" ? holder.firstElementChild : null;
    if (!on && only) only.replaceWith(...Array.from(only.childNodes));
    if (on && !only) {
      const u = target.ownerDocument.createElement("u");
      u.append(...Array.from(holder.childNodes));
      holder.append(u);
    }
  }
}

function formatOf(el: Element, typing: boolean): TextFormat {
  const size = Number.parseFloat(styleOf(el, "font-size") ?? "");
  const weight = styleOf(el, "font-weight");
  const section = el.ownerDocument.documentElement;
  const colour = styleOf(el, "color") ?? styleOf(section, "color") ?? "#000000";
  const command = (name: string) => typing && document.queryCommandState(name);
  const holders = el.localName === "ul" || el.localName === "ol" ? Array.from(el.children) : [el];
  return {
    preset: presetOf(el.localName, Number.isFinite(size) ? size : null),
    colour: hexColour(colour) ?? "#000000",
    bold: command("bold") || (weight ? weight === "bold" || Number(weight) >= 600 : HEADINGS.includes(el.localName)),
    italic: command("italic") || styleOf(el, "font-style") === "italic",
    underline: command("underline") || (holders.length > 0 && holders.every((h) => h.children.length === 1 && h.firstElementChild?.localName === "u")),
    list: el.localName === "ul" || el.localName === "ol",
    align: (["center", "right"].includes(styleOf(el, "text-align") ?? "") ? styleOf(el, "text-align") : "left") as Align,
  };
}
