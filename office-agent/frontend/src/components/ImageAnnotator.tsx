import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowToolIcon, CheckIcon, ChevronDownIcon, CloseIcon, EllipseToolIcon, LineToolIcon, PencilIcon, RectangleToolIcon, RedoIcon, TextToolIcon, TrashIcon, UndoIcon } from "./icons";
import { ANNOTATION_COLORS, STROKE_WIDTH, STROKE_WIDTHS, TEXT_SIZE, drawShapes, isNegligible, renderAnnotated, type AnnotationTool, type Shape } from "../lib/annotation";
import { useClickOutside } from "../lib/useClickOutside";

type IconType = (props: { className?: string }) => ReactNode;

const StepToolIcon: IconType = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
    <circle cx="12" cy="12" r="8.5" />
    <path d="M10.5 9.8 12.4 8.6v7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const RedactToolIcon: IconType = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
    <path d="M3.5 12s3-5.5 8.5-5.5S20.5 12 20.5 12s-3 5.5-8.5 5.5S3.5 12 3.5 12Z" strokeLinejoin="round" />
    <circle cx="12" cy="12" r="2.6" />
    <path d="M4.5 4.5l15 15" strokeLinecap="round" />
  </svg>
);

const SHAPES: Array<{ id: AnnotationTool; label: string; icon: IconType }> = [
  { id: "line", label: "Line", icon: LineToolIcon },
  { id: "arrow", label: "Arrow", icon: ArrowToolIcon },
  { id: "rectangle", label: "Rectangle", icon: RectangleToolIcon },
  { id: "ellipse", label: "Ellipse", icon: EllipseToolIcon },
  { id: "step", label: "Step", icon: StepToolIcon },
  { id: "redact", label: "Redact", icon: RedactToolIcon },
];

const toolbarButton =
  "flex h-8 items-center justify-center gap-1 rounded-lg px-1.5 text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-35 disabled:hover:bg-transparent";
const activeButton = "!bg-blue-500/15 !text-blue-600";

function Swatch({ color }: { color: string }) {
  return <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-black/15" style={{ background: color }} />;
}

/** Drop-up list for the toolbar's pickers. */
function PickerMenu<T extends string | number>({
  label,
  button,
  options,
  selected,
  active = false,
  onSelect,
}: {
  label: string;
  button: ReactNode;
  options: Array<{ id: T; label: string; leading: ReactNode }>;
  selected: T | null;
  active?: boolean;
  onSelect: (id: T) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${toolbarButton} ${active ? activeButton : open ? "bg-[var(--card-bg)] text-[var(--fg)]" : ""}`}
        onClick={() => setOpen((v) => !v)}
      >
        {button}
        <ChevronDownIcon className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div role="menu" aria-label={label} className="absolute bottom-full left-0 z-30 mb-2 min-w-44 rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] py-1.5 shadow-[var(--shadow)]">
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              role="menuitemradio"
              aria-checked={option.id === selected}
              className="flex w-full items-center gap-2.5 px-3.5 py-1.5 text-left text-sm text-[var(--fg)] hover:bg-[var(--card-bg)]"
              onClick={() => {
                onSelect(option.id);
                setOpen(false);
              }}
            >
              {option.leading}
              <span className="flex-1">{option.label}</span>
              {option.id === selected && <CheckIcon className="h-4 w-4 text-blue-500" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

type Action = { enabled: boolean; run: () => void };

function AnnotatorToolbar({
  fill,
  tool,
  color,
  width,
  saveLabel,
  saving,
  undo,
  redo,
  clear,
  onTool,
  onColor,
  onWidth,
  onClose,
  onSave,
}: {
  fill: boolean;
  tool: AnnotationTool;
  color: string;
  width: number;
  saveLabel: string;
  saving: boolean;
  undo: Action;
  redo: Action;
  clear: Action;
  onTool: (tool: AnnotationTool) => void;
  onColor: (color: string) => void;
  onWidth: (width: number) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const shape = SHAPES.find((s) => s.id === tool);
  return (
    <div
      role="toolbar"
      aria-label="Annotate"
      className={`${fill ? "absolute bottom-3" : "fixed bottom-6"} left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 whitespace-nowrap rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 shadow-[var(--shadow)]`}
    >
      <button type="button" title="Pen" aria-label="Pen" aria-pressed={tool === "pen"} className={`${toolbarButton} ${tool === "pen" ? activeButton : ""}`} onClick={() => onTool("pen")}>
        <PencilIcon className="h-4 w-4" />
      </button>
      <PickerMenu
        label="Shape"
        active={shape !== undefined}
        button={shape ? <shape.icon className="h-4 w-4" /> : <RectangleToolIcon className="h-4 w-4" />}
        options={SHAPES.map((s) => ({ id: s.id, label: s.label, leading: <s.icon className="h-4 w-4 text-[var(--muted)]" /> }))}
        selected={shape?.id ?? null}
        onSelect={onTool}
      />
      <button type="button" title="Text" aria-label="Text" aria-pressed={tool === "text"} className={`${toolbarButton} ${tool === "text" ? activeButton : ""}`} onClick={() => onTool("text")}>
        <TextToolIcon className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 w-px bg-[var(--border)]" />
      <PickerMenu
        label="Color"
        button={<Swatch color={color} />}
        options={ANNOTATION_COLORS.map((c) => ({ id: c.value, label: c.name, leading: <Swatch color={c.value} /> }))}
        selected={color}
        onSelect={onColor}
      />
      <PickerMenu
        label="Line width"
        button={<span className="block w-6 rounded-full bg-current" style={{ height: width }} />}
        options={STROKE_WIDTHS.map((w) => ({ id: w, label: `${w} px`, leading: <span className="block w-8 rounded-full bg-current text-[var(--fg)]" style={{ height: w }} /> }))}
        selected={width}
        onSelect={onWidth}
      />
      <span className="mx-1 h-5 w-px bg-[var(--border)]" />
      <button type="button" title="Undo" aria-label="Undo" disabled={!undo.enabled} className={toolbarButton} onClick={undo.run}>
        <UndoIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Redo" aria-label="Redo" disabled={!redo.enabled} className={toolbarButton} onClick={redo.run}>
        <RedoIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Clear drawing" aria-label="Clear drawing" disabled={!clear.enabled} className={toolbarButton} onClick={clear.run}>
        <TrashIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Stop annotating" aria-label="Stop annotating" className={`${toolbarButton} ml-1`} onClick={onClose}>
        <CloseIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        disabled={saving}
        className="ml-1 h-8 rounded-lg bg-[var(--primary)] px-3.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-60"
        onClick={onSave}
      >
        {saveLabel}
      </button>
    </div>

  );
}

/** What is drawn over a picture: pen, line, arrow, rectangle, ellipse, numbered steps, a box that
 * blacks out what is under it, and text. `fill` stretches the picture over its parent (the browser
 * screenshot, drawn at the page's own size); otherwise it sits in the middle of the window at the size
 * it fits. Save hands back the picture with the marks burned in and the words written on it. */
export function ImageAnnotator({
  src,
  fill = false,
  saveLabel = "Save",
  onClose,
  onSave,
}: {
  src: string;
  fill?: boolean;
  saveLabel?: string;
  onClose: () => void;
  onSave: (dataUrl: string, notes: string[]) => void;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const draftRef = useRef<Shape | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [tool, setTool] = useState<AnnotationTool>("pen");
  const [color, setColor] = useState(ANNOTATION_COLORS[0].value);
  const [width, setWidth] = useState(STROKE_WIDTH);
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [past, setPast] = useState<Shape[][]>([]);
  const [future, setFuture] = useState<Shape[][]>([]);
  const [textDraft, setTextDraft] = useState<{ x: number; y: number; value: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const commit = (next: Shape[]) => {
    setPast((p) => [...p, shapes]);
    setFuture([]);
    setShapes(next);
  };
  const undo = () => {
    if (!past.length) return;
    setFuture((f) => [shapes, ...f]);
    setShapes(past[past.length - 1]);
    setPast((p) => p.slice(0, -1));
  };
  const redo = () => {
    if (!future.length) return;
    setPast((p) => [...p, shapes]);
    setShapes(future[0]);
    setFuture((f) => f.slice(1));
  };

  const redraw = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawShapes(ctx, draftRef.current ? [...shapes, draftRef.current] : shapes, dpr);
  };

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: Math.round(entry.contentRect.width), height: Math.round(entry.contentRect.height) }));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(redraw);

  const commitText = () => {
    if (!textDraft) return;
    const shape: Shape = { kind: "text", color, at: { x: textDraft.x, y: textDraft.y }, text: textDraft.value };
    setTextDraft(null);
    if (!isNegligible(shape)) commit([...shapes, shape]);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (textDraft) return;
      const mod = e.ctrlKey || e.metaKey;
      if (e.key === "Escape") {
        // The annotator is opened over a dialog that also closes on Escape: only this one goes.
        e.stopImmediatePropagation();
        onClose();
      } else if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (mod && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  });

  const pointAt = (e: React.PointerEvent) => {
    const box = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - box.left, y: e.clientY - box.top };
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (e.button !== 0) return;
    const p = pointAt(e);
    if (tool === "text") {
      // Otherwise the press moves focus off the text box it's about to open.
      e.preventDefault();
      if (textDraft) commitText();
      setTextDraft({ x: p.x, y: p.y - TEXT_SIZE / 2, value: "" });
      return;
    }
    if (tool === "step") {
      commit([...shapes, { kind: "step", color, at: p, number: shapes.filter((s) => s.kind === "step").length + 1 }]);
      return;
    }
    e.currentTarget.setPointerCapture(e.pointerId);
    draftRef.current = tool === "pen" ? { kind: "pen", color, width, points: [p] } : tool === "redact" ? { kind: "redact", from: p, to: p } : { kind: tool, color, width, from: p, to: p };
    redraw();
  };
  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const draft = draftRef.current;
    if (!draft) return;
    const p = pointAt(e);
    if (draft.kind === "pen") draft.points.push(p);
    else if (draft.kind !== "text" && draft.kind !== "step") draft.to = p;
    redraw();
  };
  const onPointerUp = () => {
    const draft = draftRef.current;
    draftRef.current = null;
    if (draft && !isNegligible(draft)) commit([...shapes, draft]);
    else redraw();
  };

  const save = async () => {
    setSaving(true);
    try {
      const dataUrl = await renderAnnotated(src, shapes, size.width || 1);
      onSave(dataUrl, shapes.flatMap((s) => (s.kind === "text" ? [`"${s.text}"`] : [])));
    } catch {
      // The drawing stays open, so nothing is lost and Save can be retried.
    } finally {
      setSaving(false);
    }
  };

  const dpr = typeof window === "undefined" ? 1 : window.devicePixelRatio || 1;
  const picture = (
    <div ref={boxRef} className={fill ? "absolute inset-0" : "relative"}>
      <img src={src} alt="" draggable={false} className={fill ? "pointer-events-none absolute inset-0 h-full w-full select-none" : "pointer-events-none block max-h-[78vh] max-w-[92vw] select-none rounded-lg"} />
      <canvas
        ref={canvasRef}
        aria-label="Drawing area"
        width={Math.round(size.width * dpr)}
        height={Math.round(size.height * dpr)}
        style={{ width: size.width, height: size.height }}
        className={`absolute inset-0 touch-none ${tool === "text" ? "cursor-text" : "cursor-crosshair"}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      />
      {textDraft && (
        <input
          autoFocus
          aria-label="Annotation text"
          className="absolute min-w-24 border-b border-dashed bg-transparent p-0 font-semibold outline-none"
          style={{ left: textDraft.x, top: textDraft.y, color, borderColor: color, fontSize: TEXT_SIZE, lineHeight: 1.2, width: Math.max(96, (textDraft.value.length + 2) * TEXT_SIZE * 0.6) }}
          value={textDraft.value}
          onChange={(e) => setTextDraft({ ...textDraft, value: e.target.value })}
          onBlur={commitText}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitText();
            if (e.key === "Escape") setTextDraft(null);
          }}
        />
      )}
    </div>
  );

  return (
    <div className={fill ? "absolute inset-0 overflow-hidden" : "fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-6 pb-24"} data-testid="image-annotator" onClick={(e) => e.stopPropagation()}>
      {picture}
      <AnnotatorToolbar
        fill={fill}
        tool={tool}
        color={color}
        width={width}
        saveLabel={saveLabel}
        saving={saving}
        undo={{ enabled: past.length > 0, run: undo }}
        redo={{ enabled: future.length > 0, run: redo }}
        clear={{ enabled: shapes.length > 0, run: () => commit([]) }}
        onTool={setTool}
        onColor={setColor}
        onWidth={setWidth}
        onClose={onClose}
        onSave={() => void save()}
      />
    </div>
  );
}

/** The pencil in a picture's preview: opens the annotator over it, and hands the marked copy on. */
export function AnnotateEntry({ src, onSaved }: { src: string; onSaved: (dataUrl: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        title="Annotate image"
        aria-label="Annotate image"
        className="ml-auto flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--card-bg)]"
        onClick={() => setOpen(true)}
      >
        <PencilIcon className="h-5 w-5" />
      </button>
      {open && (
        <ImageAnnotator
          src={src}
          onClose={() => setOpen(false)}
          onSave={(dataUrl) => {
            setOpen(false);
            onSaved(dataUrl);
          }}
        />
      )}
    </>
  );
}
