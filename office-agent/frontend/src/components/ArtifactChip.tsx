import { useEffect, useRef, useState } from "react";
import { KINDS, type ArtifactKind } from "../lib/artifacts";
import { getDesignSystems } from "../lib/rest";
import { useClickOutside } from "../lib/useClickOutside";
import type { DesignSystemSummary } from "../types/settings";
import { CheckIcon } from "./icons";

const item = "flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]";

/** A Slides conversation's choice of design system: the library's systems, none, or the page that manages them. */
function DesignSystemChoice({ chosen, onChoose, onManage }: { chosen: string | null; onChoose: (id: string | null) => void; onManage: () => void }) {
  const [open, setOpen] = useState(false);
  const [systems, setSystems] = useState<DesignSystemSummary[] | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);
  useEffect(() => {
    let live = true;
    getDesignSystems().then((found) => live && setSystems(found), () => live && setSystems([]));
    return () => {
      live = false;
    };
  }, []);
  const toggle = () => setOpen((v) => !v);
  const name = systems?.find((s) => s.id === chosen)?.name;
  const pick = (id: string | null) => {
    setOpen(false);
    onChoose(id);
  };
  return (
    <div className="relative" ref={rootRef}>
      <button type="button" aria-haspopup="menu" aria-expanded={open} className="ml-1.5 inline-flex h-6 items-center rounded-lg px-2 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]" onClick={toggle}>
        Design system: {chosen ? (name ?? "chosen") : "none"}
      </button>
      {open && (
        <div role="menu" className="absolute bottom-full left-0 z-20 mb-1 w-64 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]">
          <button type="button" role="menuitemradio" aria-checked={chosen === null} className={item} onClick={() => pick(null)}>
            <span className="min-w-0 flex-1 truncate">No design system</span>
            {chosen === null && <CheckIcon className="h-4 w-4 shrink-0" />}
          </button>
          {(systems ?? []).map((system) => (
            <button key={system.id} type="button" role="menuitemradio" aria-checked={chosen === system.id} className={item} onClick={() => pick(system.id)}>
              <span className="min-w-0 flex-1 truncate">{system.name}</span>
              {chosen === system.id && <CheckIcon className="h-4 w-4 shrink-0" />}
            </button>
          ))}
          <div className="my-1 border-t border-[var(--border)]" />
          <button type="button" role="menuitem" className={item} onClick={() => { setOpen(false); onManage(); }}>
            {systems !== null && systems.length === 0 ? "Make a design system…" : "Manage design systems…"}
          </button>
        </div>
      )}
    </div>
  );
}

/** The kind a new conversation's first message is to make, in the message box; Remove drops it. A Slides one also offers a design system. */
export function ArtifactChip({
  kind,
  designSystem,
  onDesignSystem,
  onManageDesignSystems,
  onRemove,
}: {
  kind: ArtifactKind;
  designSystem: string | null;
  onDesignSystem: (id: string | null) => void;
  onManageDesignSystems: () => void;
  onRemove: () => void;
}) {
  const { colour, label } = KINDS[kind];
  return (
    <div className="mb-1.5 flex items-center">
      <span className="inline-flex items-center gap-1 rounded-lg py-0.5 pl-2 pr-1 text-xs font-medium" style={{ background: `color-mix(in srgb, ${colour} 14%, var(--bg))`, color: colour }}>
        {label}
        <button type="button" aria-label={`Remove ${label} mode`} className="flex h-4 w-4 items-center justify-center rounded-full hover:bg-[var(--border)]" onClick={onRemove}>
          ×
        </button>
      </span>
      {kind === "slides" && <DesignSystemChoice chosen={designSystem} onChoose={onDesignSystem} onManage={onManageDesignSystems} />}
    </div>
  );
}
