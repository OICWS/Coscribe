import { hexColour, setStyle, styleOf } from "./slideSource";

/** A shape's border as the section language writes it: `none`, or `Npx solid|dashed #RRGGBB`. */
export interface Border {
  kind: "none" | "solid" | "dashed";
  width: number;
  colour: string;
}

export const DEFAULT_BORDER: Border = { kind: "solid", width: 2, colour: "#1F2937" };

export function parseBorder(text: string | null): Border {
  const match = /^(\d+(?:\.\d+)?)px\s+(solid|dashed)\s+(#[0-9a-fA-F]{6})$/.exec((text ?? "").trim());
  if (!match) return { ...DEFAULT_BORDER, kind: "none" };
  return { kind: match[2] as Border["kind"], width: Number(match[1]), colour: match[3].toUpperCase() };
}

export const borderText = (border: Border) => (border.kind === "none" ? "none" : `${border.width}px ${border.kind} ${border.colour}`);

export const readBorder = (el: Element) => parseBorder(styleOf(el, "border"));

/** `none` takes the border off (the panel does not offer it for a line, which is its border). */
export const setBorder = (el: Element, border: Border) => setStyle(el, "border", border.kind === "none" ? null : borderText(border));

export const readOpacity = (el: Element) => {
  const n = Number.parseFloat(styleOf(el, "opacity") ?? "");
  return Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 1;
};

export const setOpacity = (el: Element, opacity: number) =>
  setStyle(el, "opacity", opacity >= 1 ? null : String(Math.round(Math.min(1, Math.max(0, opacity)) * 100) / 100));

export const readFill = (el: Element) => hexColour(styleOf(el, "background") ?? "");

export const readRadius = (el: Element) => {
  const n = Number.parseFloat(styleOf(el, "border-radius") ?? "");
  return Number.isFinite(n) ? n : null;
};

export const setRadius = (el: Element, radius: number) => setStyle(el, "border-radius", `${Math.max(0, Math.round(radius))}px`);

export type Fit = "cover" | "contain" | "fill";
export const readFit = (el: Element): Fit => {
  const fit = styleOf(el, "object-fit");
  return fit === "contain" || fit === "fill" ? fit : "cover";
};
export const setFit = (el: Element, fit: Fit) => setStyle(el, "object-fit", fit);

/** An outer shadow as the section language writes it: `Xpx Ypx BLURpx #RRGGBB [opacity]`. */
export interface Shadow {
  x: number;
  y: number;
  blur: number;
  colour: string;
  opacity: number;
}

export const DEFAULT_SHADOW: Shadow = { x: 0, y: 6, blur: 18, colour: "#000000", opacity: 0.25 };

function parseShadow(text: string | null): Shadow | null {
  const match = /^(-?\d+(?:\.\d+)?)px\s+(-?\d+(?:\.\d+)?)px\s+(\d+(?:\.\d+)?)px\s+(#[0-9a-fA-F]{6})(?:\s+(\d(?:\.\d+)?))?$/.exec((text ?? "").trim());
  if (!match) return null;
  return { x: Number(match[1]), y: Number(match[2]), blur: Number(match[3]), colour: match[4].toUpperCase(), opacity: match[5] === undefined ? 0.35 : Number(match[5]) };
}

const shadowText = (s: Shadow) => `${s.x}px ${s.y}px ${s.blur}px ${s.colour} ${Math.round(Math.min(1, Math.max(0, s.opacity)) * 100) / 100}`;

export const readShadow = (el: Element) => parseShadow(styleOf(el, "box-shadow"));

/** `null` takes the shadow off. */
export const setShadow = (el: Element, shadow: Shadow | null) => setStyle(el, "box-shadow", shadow ? shadowText({ ...shadow, blur: Math.max(0, shadow.blur) }) : null);
