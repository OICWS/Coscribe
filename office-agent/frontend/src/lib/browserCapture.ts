/** Same shape as the composer's pending images, so a capture joins the
 * message as-is; `text`/`tag` carry what the element says, which a model
 * can't reliably read back off a screenshot. */
export interface BrowserCapture {
  name: string;
  dataUrl: string;
  text?: string;
  tag?: string;
  /** An annotated screenshot, whose `text` is already the whole note. */
  source?: "annotation";
}
