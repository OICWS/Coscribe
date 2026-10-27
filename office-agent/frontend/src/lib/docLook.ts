export type Face = "serif" | "sans";

/** How the person likes to read a Doc: kept in this browser, not in the file, so it changes no document. */
export interface DocLook {
  headings: Face;
  text: Face;
  wide: boolean;
}

const KEY = "coscribe.doc.look";
const DEFAULT: DocLook = { headings: "serif", text: "sans", wide: false };

export function loadLook(): DocLook {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? "null") as Partial<DocLook> | null;
    const face = (value: unknown, fallback: Face): Face => (value === "serif" || value === "sans" ? value : fallback);
    return { headings: face(stored?.headings, DEFAULT.headings), text: face(stored?.text, DEFAULT.text), wide: stored?.wide === true };
  } catch {
    return DEFAULT;
  }
}

export function saveLook(look: DocLook) {
  try {
    localStorage.setItem(KEY, JSON.stringify(look));
  } catch {
    // Private windows and blocked storage: the look then lasts until the panel closes.
  }
}
