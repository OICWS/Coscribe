/** Shapes drawn over a page screenshot in the Browser panel, in the
 * screenshot's on-screen (CSS pixel) coordinates. */

export type AnnotationTool = "pen" | "line" | "arrow" | "rectangle" | "ellipse" | "step" | "redact" | "text";

export interface AnnotationColor {
  name: string;
  value: string;
}

export const ANNOTATION_COLORS: AnnotationColor[] = [
  { name: "Red", value: "#e03131" },
  { name: "Blue", value: "#1c7ed6" },
  { name: "Green", value: "#2f9e44" },
  { name: "Black", value: "#1f1f1f" },
  { name: "White", value: "#ffffff" },
];

type Point = { x: number; y: number };

export type Shape =
  | { kind: "pen"; color: string; width: number; points: Point[] }
  | { kind: "line" | "arrow" | "rectangle" | "ellipse"; color: string; width: number; from: Point; to: Point }
  | { kind: "redact"; from: Point; to: Point }
  | { kind: "step"; color: string; at: Point; number: number }
  | { kind: "text"; color: string; at: Point; text: string };

/** The line widths the toolbar offers, thin to thick, in on-screen pixels. */
export const STROKE_WIDTHS = [2, 3, 5, 8];
export const STROKE_WIDTH = STROKE_WIDTHS[1];
export const TEXT_SIZE = 18;
const STEP_RADIUS = 13;

/** Draws `shapes` onto `ctx`, scaled from on-screen coordinates by
 * `scale` (the export uses the screenshot's full pixel size). */
export function drawShapes(ctx: CanvasRenderingContext2D, shapes: readonly Shape[], scale: number): void {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const shape of shapes) {
    ctx.lineWidth = ("width" in shape ? shape.width : STROKE_WIDTH) * scale;
    if (shape.kind === "redact") {
      ctx.fillStyle = "#000000";
      const { from, to } = shape;
      ctx.fillRect(Math.min(from.x, to.x) * scale, Math.min(from.y, to.y) * scale, Math.abs(to.x - from.x) * scale, Math.abs(to.y - from.y) * scale);
      continue;
    }
    ctx.strokeStyle = shape.color;
    ctx.fillStyle = shape.color;
    if (shape.kind === "step") {
      ctx.beginPath();
      ctx.arc(shape.at.x * scale, shape.at.y * scale, STEP_RADIUS * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = shape.color === "#ffffff" ? "#1f1f1f" : "#ffffff";
      ctx.font = `700 ${STEP_RADIUS * 1.15 * scale}px system-ui, -apple-system, "Segoe UI", sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(shape.number), shape.at.x * scale, shape.at.y * scale + scale * 0.5);
      ctx.textAlign = "start";
    } else if (shape.kind === "pen") {
      ctx.beginPath();
      shape.points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x * scale, p.y * scale) : ctx.lineTo(p.x * scale, p.y * scale)));
      if (shape.points.length === 1) ctx.lineTo(shape.points[0].x * scale + 0.1, shape.points[0].y * scale);
      ctx.stroke();
    } else if (shape.kind === "text") {
      ctx.font = `600 ${TEXT_SIZE * scale}px system-ui, -apple-system, "Segoe UI", sans-serif`;
      ctx.textBaseline = "top";
      // A thin contrasting outline keeps the note readable on any page.
      ctx.lineWidth = 3 * scale;
      ctx.strokeStyle = shape.color === "#ffffff" ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.85)";
      ctx.strokeText(shape.text, shape.at.x * scale, shape.at.y * scale);
      ctx.fillText(shape.text, shape.at.x * scale, shape.at.y * scale);
    } else {
      const x1 = shape.from.x * scale;
      const y1 = shape.from.y * scale;
      const x2 = shape.to.x * scale;
      const y2 = shape.to.y * scale;
      ctx.beginPath();
      if (shape.kind === "rectangle") {
        ctx.rect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
      } else if (shape.kind === "ellipse") {
        ctx.ellipse((x1 + x2) / 2, (y1 + y2) / 2, Math.abs(x2 - x1) / 2, Math.abs(y2 - y1) / 2, 0, 0, Math.PI * 2);
      } else {
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        if (shape.kind === "arrow") {
          const angle = Math.atan2(y2 - y1, x2 - x1);
          const head = (10 + shape.width * 1.5) * scale;
          for (const side of [-1, 1]) {
            ctx.moveTo(x2, y2);
            ctx.lineTo(x2 - head * Math.cos(angle + (side * Math.PI) / 7), y2 - head * Math.sin(angle + (side * Math.PI) / 7));
          }
        }
      }
      ctx.stroke();
    }
  }
}

/** A shape too small to be deliberate (a click with a drag tool). */
export function isNegligible(shape: Shape): boolean {
  if (shape.kind === "pen") return shape.points.length === 0;
  if (shape.kind === "step") return false;
  if (shape.kind === "text") return !shape.text.trim();
  return Math.hypot(shape.to.x - shape.from.x, shape.to.y - shape.from.y) < 4;
}

/** The screenshot with the shapes burned in, at the screenshot's own
 * resolution, as a JPEG data URL. `displayWidth` is the on-screen width
 * the shapes were drawn against. */
export async function renderAnnotated(screenshotUrl: string, shapes: readonly Shape[], displayWidth: number): Promise<string> {
  const image = new Image();
  image.src = screenshotUrl;
  await image.decode();
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas isn't available.");
  // A JPEG has no transparency: what the picture leaves clear becomes white, not black.
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
  drawShapes(ctx, shapes, image.naturalWidth / displayWidth);
  return canvas.toDataURL("image/jpeg", 0.9);
}

/** The pending pictures with the marked copy of the one named `name` after them. */
export const withAnnotatedCopy = <T extends { name: string; dataUrl: string }>(pending: T[], name: string, dataUrl: string): T[] => [
  ...pending,
  { name: `${name.replace(/\.[^.]+$/, "")}-annotated.jpg`, dataUrl } as T,
];
