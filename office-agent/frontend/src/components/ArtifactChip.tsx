import { KINDS, type ArtifactKind } from "../lib/artifacts";

/** The kind a new conversation's first message is to make, in the message box; Remove drops it. */
export function ArtifactChip({ kind, onRemove }: { kind: ArtifactKind; onRemove: () => void }) {
  const { colour, label } = KINDS[kind];
  return (
    <div className="mb-1.5 flex">
      <span className="inline-flex items-center gap-1 rounded-lg py-0.5 pl-2 pr-1 text-xs font-medium" style={{ background: `color-mix(in srgb, ${colour} 14%, var(--bg))`, color: colour }}>
        {label}
        <button type="button" aria-label={`Remove ${label} mode`} className="flex h-4 w-4 items-center justify-center rounded-full hover:bg-[var(--border)]" onClick={onRemove}>
          ×
        </button>
      </span>
    </div>
  );
}
