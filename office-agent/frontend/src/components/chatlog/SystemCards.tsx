import { useContext } from "react";
import { PAGE_KINDS } from "../../lib/artifacts";
import { savedSystems } from "../../lib/savedSystems";
import { ChevronRightIcon } from "../icons";
import { KindIcon } from "../artifacts/artifactIcons";
import { OpenDesignSystem } from "./contexts";
import type { ToolOrApprovalItem } from "./types";

/** The design systems a run of calls saved, each a card that opens it in Settings. */
export function SystemCards({ items }: { items: ToolOrApprovalItem[] }) {
  const open = useContext(OpenDesignSystem);
  const systems = savedSystems(items);
  if (!open || systems.length === 0) return null;
  const { colour } = PAGE_KINDS["design-system"];
  return (
    <div className="mt-2 flex flex-col gap-2">
      {systems.map((system) => (
        <button
          key={system.id}
          type="button"
          title={`Open ${system.name}`}
          className="flex w-full max-w-[460px] items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-left hover:bg-[var(--card-bg)]"
          onClick={() => open(system.id)}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ color: colour, background: `color-mix(in srgb, ${colour} 14%, transparent)` }}>
            <KindIcon kind="design-system" className="h-5 w-5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">{system.name}</span>
            <span className="block truncate text-xs text-[var(--muted)]">Design system{system.summary && ` · ${system.summary}`}</span>
          </span>
          <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        </button>
      ))}
    </div>
  );
}
