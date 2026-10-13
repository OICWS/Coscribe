import { PptxShapeOverlay, type PptxShapeCapture } from "../PptxShapeOverlay";
import { type ToolOrApprovalItem } from "./types";
import { previewPathOf, pptxOverlayTargetOf } from "./helpers";

/** A finished write_docx/xlsx/pptx call's thumbnail; a .pptx one is
 * clickable to target a shape in a follow-up edit. */
export function ToolPreview({
  item,
  onPptxShapePicked,
}: {
  item: ToolOrApprovalItem;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const previewPath = previewPathOf(item.result);
  if (!previewPath) return null;
  const pptxTarget = pptxOverlayTargetOf(item.arguments);
  const src = `/api/previews/${encodeURIComponent(previewPath)}`;
  const className = "my-1.5 block max-h-32 rounded-lg border border-[var(--border)]";
  return pptxTarget ? (
    <PptxShapeOverlay
      src={src}
      alt={`${item.toolName} preview`}
      className={className}
      path={pptxTarget.path}
      slide={pptxTarget.slide}
      onPick={onPptxShapePicked}
    />
  ) : (
    <img src={src} alt={`${item.toolName} preview`} className={className} />
  );
}
