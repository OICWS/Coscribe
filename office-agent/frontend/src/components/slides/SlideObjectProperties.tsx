import { useRef } from "react";
import { DEFAULT_BORDER, readBorder, readFill, readFit, readOpacity, readRadius, setBorder, setFit, setOpacity, setRadius, type Fit } from "../../lib/slideShape";
import { setFill, type DesignSystem } from "../../lib/slideText";
import { ColourField, NumberField, Row, Section, Segmented, field } from "./PropertyRows";
import type { EditorSelection } from "./SlideTextProperties";

const FITS: { value: Fit; title: string }[] = [
  { value: "cover", title: "Cover" },
  { value: "contain", title: "Contain" },
  { value: "fill", title: "Stretch" },
];

/** A picture's properties: which file, how it fits its box, its alternative text, and its look. */
export function ImageProperties({ selection, design }: { selection: EditorSelection; design: DesignSystem | null }) {
  const { element: img, edit, upload } = selection;
  const fileRef = useRef<HTMLInputElement>(null);
  const src = img.getAttribute("src") ?? "";
  const alt = img.getAttribute("alt") ?? "";
  const redraw: Redraw = (change) => edit(change, true);
  return (
    <>
      <Section title="Image">
        <Row label="Image">
          <button type="button" aria-label="Replace the picture" title="Replace the picture" className={field} onClick={() => fileRef.current?.click()}>
            <span className="flex-1 truncate text-left">{src.split("/").pop() || "No picture"}</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            hidden
            accept="image/png,image/jpeg,image/gif,image/webp"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file && upload) void upload(file).then((picture) => edit((el) => el.setAttribute("src", picture.src), true));
            }}
          />
        </Row>
        <Row label="Fit">
          <Segmented label="Fit" value={readFit(img)} choices={FITS.map((f) => ({ ...f, icon: <span className="text-xs">{f.title}</span> }))} onChange={(fit) => edit((el) => setFit(el, fit), true)} />
        </Row>
        <Row label="Alt text">
          <label className={field}>
            <input
              aria-label="Alt text"
              className="h-full min-w-0 flex-1 bg-transparent outline-none"
              defaultValue={alt}
              key={alt}
              onBlur={(e) => e.target.value !== alt && edit((el) => (e.target.value ? el.setAttribute("alt", e.target.value) : el.removeAttribute("alt")), false)}
              onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
            />
          </label>
        </Row>
      </Section>
      <Section title="Appearance">
        <OpacityRow shape={img} redraw={redraw} />
        <Row label="Radius">
          <NumberField label="Radius" unit="px" value={readRadius(img) ?? 0} onCommit={(n) => redraw((el) => setRadius(el, n))} />
        </Row>
        <BorderRows shape={img} redraw={redraw} colours={design?.palette ?? []} allowNone />
      </Section>
    </>
  );
}

const BORDERS = ["none", "solid", "dashed"] as const;

type Redraw = (change: (el: Element) => void) => void;

function OpacityRow({ shape, redraw }: { shape: Element; redraw: Redraw }) {
  return (
    <Row label="Opacity">
      <NumberField label="Opacity" value={readOpacity(shape)} onCommit={(n) => redraw((el) => setOpacity(el, n))} />
      <input
        type="range"
        aria-label="Opacity slider"
        min={0}
        max={1}
        step={0.05}
        value={readOpacity(shape)}
        className="min-w-0 flex-1"
        onChange={(e) => redraw((el) => setOpacity(el, Number(e.target.value)))}
      />
    </Row>
  );
}

/** The border's style, and its width and colour when there is one. */
function BorderRows({ shape, redraw, colours, allowNone }: { shape: Element; redraw: Redraw; colours: string[]; allowNone: boolean }) {
  const border = readBorder(shape);
  return (
    <>
      <Row label="Border">
        <Segmented
          label="Border style"
          value={border.kind}
          choices={BORDERS.filter((b) => allowNone || b !== "none").map((b) => ({ value: b, title: b === "none" ? "No border" : `${b[0].toUpperCase()}${b.slice(1)} border`, icon: <span className="text-xs">{b === "none" ? "None" : b === "solid" ? "—" : "- -"}</span> }))}
          onChange={(b) => redraw((el) => setBorder(el, { ...(border.kind === "none" ? DEFAULT_BORDER : border), kind: b }))}
        />
      </Row>
      {border.kind !== "none" && (
        <>
          <Row label="Width">
            <NumberField label="Border width" unit="px" value={border.width} onCommit={(n) => redraw((el) => setBorder(el, { ...border, width: Math.max(1, n) }))} />
          </Row>
          <Row label="Color">
            <ColourField label="Border colour" value={border.colour} colours={colours} onPick={(c) => redraw((el) => setBorder(el, { ...border, colour: c }))} />
          </Row>
        </>
      )}
    </>
  );
}

/** A shape's appearance: fill, opacity, corner radius (a rounded rectangle) and border. */
export function ShapeProperties({ selection, design }: { selection: EditorSelection; design: DesignSystem | null }) {
  const { element: shape, edit } = selection;
  // A container's card is a rounded rectangle whose radius is its own.
  const kind = selection.kind === "container" ? "round-rect" : (shape.getAttribute("data-shape") ?? "rect");
  const colours = design?.palette ?? [];
  const redraw = (change: (el: Element) => void) => edit(change, true);
  return (
    <Section title="Appearance">
      {kind !== "line" && (
        <Row label="Background">
          <ColourField label="Background" value={readFill(shape)} colours={colours} onPick={(c) => redraw((el) => setFill(el, c))} onClear={() => redraw((el) => setFill(el, null))} />
        </Row>
      )}
      <OpacityRow shape={shape} redraw={redraw} />
      {kind === "round-rect" && (
        <Row label="Radius">
          <NumberField label="Radius" unit="px" value={readRadius(shape) ?? 0} onCommit={(n) => redraw((el) => setRadius(el, n))} />
        </Row>
      )}
      <BorderRows shape={shape} redraw={redraw} colours={colours} allowNone={kind !== "line"} />
    </Section>
  );
}
