import { PptxShapeOverlay, type PptxShapeCapture } from "../PptxShapeOverlay";

/** A pptx edit's before/after slide render, side by side -- what
 * conversation/session.py's _build_pptx_edit_preview sends alongside a raw
 * arguments dump, so approving `{"shape_index": 3, "fill_color":
 * "38BDF8"}` doesn't require reading JSON to picture the result. Either
 * side can be missing on its own (the dry run failed, or there was
 * nothing to diff against) -- rendered as a muted placeholder rather than
 * collapsing the layout, so "before" and "after" always line up.
 * `pptxTarget` (present only for a real .pptx edit -- see
 * pptxOverlayTargetOf) makes both sides clickable the same way
 * ToolCallRow's own completed-call thumbnail is, so picking a shape to
 * target a *follow-up* edit doesn't require waiting for this one to
 * resolve first. */
export function ApprovalPreview({
  beforePreview,
  afterPreview,
  pptxTarget,
  onPptxShapePicked,
}: {
  beforePreview?: string | null;
  afterPreview?: string | null;
  pptxTarget: { path: string; slide: number } | null;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  return (
    <div className="mb-1.5 grid grid-cols-2 gap-2">
      {(
        [
          ["Before", beforePreview],
          ["After", afterPreview],
        ] as const
      ).map(([label, name]) => (
        <div key={label} className="flex flex-col gap-1">
          <div className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted)]">{label}</div>
          {name ? (
            pptxTarget ? (
              <PptxShapeOverlay
                src={`/api/previews/${encodeURIComponent(name)}`}
                alt={`${label} the edit`}
                className="block w-full rounded-lg border border-[var(--border)]"
                path={pptxTarget.path}
                slide={pptxTarget.slide}
                onPick={onPptxShapePicked}
              />
            ) : (
              <img
                src={`/api/previews/${encodeURIComponent(name)}`}
                alt={`${label} the edit`}
                className="block w-full rounded-lg border border-[var(--border)]"
              />
            )
          ) : (
            <div className="flex aspect-[4/3] w-full items-center justify-center rounded-lg border border-dashed border-[var(--border)] text-[10px] text-[var(--muted)]">
              no preview
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
