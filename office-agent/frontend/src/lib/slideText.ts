import { hexColour, retag, setStyle, styleOf } from "./slideSource";

/** One of the deck's named text styles (decision 0017). */
export interface TextStyle {
  id: string;
  name: string;
  size: number;
  weight: number;
  line_height: number;
  letter_spacing: number;
}

export interface DesignSystem {
  name: string;
  palette: string[];
  fonts: string[];
  styles: TextStyle[];
}

export type ListKind = "none" | "bullet" | "numbered";
export type TextAlign = "left" | "center" | "right" | "justify";

/** What the properties panel shows for a text element. */
export interface TextValues {
  styleId: string | null;
  font: string;
  bold: boolean;
  size: number;
  lineHeight: number;
  letterSpacing: number;
  colour: string;
  italic: boolean;
  underline: boolean;
  list: ListKind;
  align: TextAlign;
  padding: number;
  background: string | null;
}

/** The section language's own defaults, for a value the element does not set. */
const DEFAULT_SIZE: Record<string, number> = { h1: 64, h2: 48, h3: 36 };
const DEFAULT_LINE: Record<string, number> = { h1: 1.15, h2: 1.15, h3: 1.2 };
const DEFAULT_FONT = "Microsoft YaHei, Arial";
/** The tag a style's text takes: a heading style a heading, any other a paragraph. */
const STYLE_TAG: Record<string, string> = { "heading-1": "h1", "heading-3": "h3" };
export const LINE_HEIGHT = { min: 1, max: 2.5 };

const px = (value: string | null): number | null => {
  const n = Number.parseFloat(value ?? "");
  return Number.isFinite(n) ? n : null;
};

export const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** The first family of a font stack: what the panel calls the font. */
export const familyName = (stack: string) => stack.split(",")[0].trim().replace(/^["']|["']$/g, "");

export const isBold = (weight: string | null, fallback: boolean) => (weight === null ? fallback : weight === "bold" || Number(weight) >= 600);

const holders = (el: Element) => (el.localName === "ul" || el.localName === "ol" ? Array.from(el.children) : [el]);

export function textValues(el: Element): TextValues {
  const section = el.ownerDocument.documentElement;
  const tag = el.localName;
  const align = styleOf(el, "text-align");
  return {
    styleId: el.getAttribute("data-text-style"),
    font: styleOf(el, "font-family") ?? styleOf(section, "font-family") ?? DEFAULT_FONT,
    bold: isBold(styleOf(el, "font-weight"), tag in DEFAULT_SIZE),
    size: px(styleOf(el, "font-size")) ?? DEFAULT_SIZE[tag] ?? 28,
    lineHeight: px(styleOf(el, "line-height")) ?? DEFAULT_LINE[tag] ?? 1.35,
    letterSpacing: px(styleOf(el, "letter-spacing")) ?? 0,
    colour: hexColour(styleOf(el, "color") ?? styleOf(section, "color") ?? "") ?? "#000000",
    italic: styleOf(el, "font-style") === "italic",
    underline: holders(el).every((h) => h.children.length === 1 && h.firstElementChild?.localName === "u"),
    list: tag === "ul" ? "bullet" : tag === "ol" ? "numbered" : "none",
    align: align === "center" || align === "right" || align === "justify" ? align : "left",
    padding: px(styleOf(el, "padding")) ?? 0,
    background: hexColour(styleOf(el, "background") ?? ""),
  };
}

/** Takes the element off its named style: a value the style sets was changed by hand. */
const overridden = (el: Element) => el.removeAttribute("data-text-style");

/** Gives the element the style's values and marks it with the style's id. */
export function applyTextStyle(el: Element, style: TextStyle): Element {
  const isList = el.localName === "ul" || el.localName === "ol";
  const next = isList ? el : retag(el, STYLE_TAG[style.id] ?? "p");
  setStyle(next, "font-size", `${style.size}px`);
  setStyle(next, "font-weight", String(style.weight));
  setStyle(next, "line-height", String(style.line_height));
  setStyle(next, "letter-spacing", style.letter_spacing ? `${style.letter_spacing}px` : null);
  next.setAttribute("data-text-style", style.id);
  return next;
}

export function setFont(el: Element, stack: string) {
  overridden(el);
  setStyle(el, "font-family", stack);
}

export function setBold(el: Element, bold: boolean) {
  overridden(el);
  setStyle(el, "font-weight", bold ? "700" : "400");
}

export function setSize(el: Element, size: number) {
  overridden(el);
  setStyle(el, "font-size", `${clamp(Math.round(size), 1, 600)}px`);
}

export function setLineHeight(el: Element, height: number) {
  overridden(el);
  setStyle(el, "line-height", String(Math.round(clamp(height, LINE_HEIGHT.min, LINE_HEIGHT.max) * 100) / 100));
}

export function setLetterSpacing(el: Element, spacing: number) {
  overridden(el);
  setStyle(el, "letter-spacing", spacing ? `${clamp(spacing, -20, 100)}px` : null);
}

export const setItalic = (el: Element, on: boolean) => setStyle(el, "font-style", on ? "italic" : null);
export const setAlign = (el: Element, align: TextAlign) => setStyle(el, "text-align", align === "left" ? null : align);
export const setPadding = (el: Element, padding: number) => setStyle(el, "padding", padding ? `${clamp(Math.round(padding), 0, 400)}px` : null);
export const setFill = (el: Element, colour: string | null) => setStyle(el, "background", colour);

export function setList(el: Element, list: ListKind): Element {
  const tag = list === "bullet" ? "ul" : list === "numbered" ? "ol" : "p";
  if (el.localName === tag) return el;
  if (tag === "p" || (el.localName !== "ul" && el.localName !== "ol")) return retag(el, tag);
  // One kind of list to the other: the items stay as they are.
  const next = el.ownerDocument.createElement(tag);
  for (const attr of Array.from(el.attributes)) next.setAttribute(attr.name, attr.value);
  next.append(...Array.from(el.childNodes));
  el.replaceWith(next);
  return next;
}

/** Underlines all of the element's text, or takes its underline off; a list item by item. */
export function setUnderline(el: Element, on: boolean) {
  for (const holder of holders(el)) {
    const only = holder.children.length === 1 && holder.firstElementChild?.localName === "u" ? holder.firstElementChild : null;
    if (!on && only) only.replaceWith(...Array.from(only.childNodes));
    if (on && !only) {
      const u = el.ownerDocument.createElement("u");
      u.append(...Array.from(holder.childNodes));
      holder.append(u);
    }
  }
}
