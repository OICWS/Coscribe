import { useEffect, useRef, useState, type ReactNode } from "react";
import { PAGE_KINDS, type PageKind } from "../lib/artifacts";
import { getDesignSystems } from "../lib/rest";
import { useClickOutside } from "../lib/useClickOutside";
import type { DesignSystemSummary } from "../types/settings";
import { CheckIcon, ChevronDownIcon, CloseIcon, ExternalLinkIcon, PlusIcon } from "./icons";

const NOUNS: Record<PageKind, string> = { docs: "document", slides: "deck", design: "design", dashboard: "dashboard", "design-system": "design system" };
const item = "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--card-bg)]";
const menu = "absolute bottom-full left-0 z-20 mb-2 min-w-72 max-w-96 rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 shadow-[var(--shadow)]";

/** A pill in the message box that opens a small menu above it. */
function PillMenu({ pill, children }: { pill: (props: { open: boolean; onClick: () => void }) => ReactNode; children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);
  return (
    <div className="relative shrink-0" ref={rootRef}>
      {pill({ open, onClick: () => setOpen((v) => !v) })}
      {open && (
        <div role="menu" className={menu}>
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

/** A Slides conversation's choice of design system: the library's systems, or the way to make or manage them. */
function DesignSystemChoice({ chosen, onChoose, onManage }: { chosen: string | null; onChoose: (id: string | null) => void; onManage: (startNew: boolean) => void }) {
  const [systems, setSystems] = useState<DesignSystemSummary[] | null>(null);
  // Fetched when the chip appears, not when its menu opens: the message box is laid out again as a
  // new conversation connects, which would close a menu that was waiting for its list.
  useEffect(() => {
    let live = true;
    getDesignSystems().then((found) => live && setSystems(found), () => live && setSystems([]));
    return () => {
      live = false;
    };
  }, []);
  const name = systems?.find((s) => s.id === chosen)?.name;
  return (
    <PillMenu
      pill={({ open, onClick }) => (
        <button type="button" aria-haspopup="menu" aria-expanded={open} className="inline-flex h-7 max-w-64 items-center gap-1 rounded-lg bg-[var(--card-bg)] px-2.5 text-sm hover:bg-[var(--border)]" onClick={onClick}>
          <span className="truncate">{chosen ? (name ?? "Design system") : "Choose design system…"}</span>
          <ChevronDownIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
        </button>
      )}
    >
      {(close) => (
        <>
          {(systems ?? []).map((system) => (
            <button key={system.id} type="button" role="menuitemradio" aria-checked={chosen === system.id} className={item} onClick={() => { close(); onChoose(system.id); }}>
              <span className="min-w-0 flex-1 truncate">{system.name}</span>
              {chosen === system.id && <CheckIcon className="h-4 w-4 shrink-0" />}
            </button>
          ))}
          {chosen !== null && (
            <button type="button" role="menuitem" className={item} onClick={() => { close(); onChoose(null); }}>
              <CloseIcon className="h-4 w-4 shrink-0" /> No design system
            </button>
          )}
          {(systems ?? []).length > 0 && <div className="my-1 border-t border-[var(--border)]" />}
          <button type="button" role="menuitem" className={item} onClick={() => { close(); onManage(false); }}>
            <ExternalLinkIcon className="h-4 w-4 shrink-0" /> Manage design systems
          </button>
          <button type="button" role="menuitem" className={item} onClick={() => { close(); onManage(true); }}>
            <PlusIcon className="h-4 w-4 shrink-0" /> Make a new design system first
          </button>
        </>
      )}
    </PillMenu>
  );
}

/** What the new conversation's first message is to make, left of the message box: the kind (a click offers Remove)
 * and, for Slides, a design system. */
export function ArtifactChip({
  kind,
  designSystem,
  onDesignSystem,
  onManageDesignSystems,
  onRemove,
}: {
  kind: PageKind;
  designSystem: string | null;
  onDesignSystem: (id: string | null) => void;
  onManageDesignSystems: (startNew: boolean) => void;
  onRemove: () => void;
}) {
  const { colour, label } = PAGE_KINDS[kind];
  return (
    <div className="mr-2 flex shrink-0 items-center gap-1.5">
      <PillMenu
        pill={({ open, onClick }) => (
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={open}
            aria-label={`${label} mode`}
            className="inline-flex h-7 items-center rounded-lg px-2.5 text-sm font-medium"
            style={{ background: `color-mix(in srgb, ${colour} 14%, var(--bg))`, color: colour }}
            onClick={onClick}
          >
            {label}
          </button>
        )}
      >
        {(close) => (
          <button type="button" role="menuitem" className={item} onClick={() => { close(); onRemove(); }}>
            <CloseIcon className="h-4 w-4 shrink-0" /> Remove {NOUNS[kind]}
          </button>
        )}
      </PillMenu>
      {kind === "slides" && <DesignSystemChoice chosen={designSystem} onChoose={onDesignSystem} onManage={onManageDesignSystems} />}
    </div>
  );
}
