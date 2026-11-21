import { useEffect, useRef, useState } from "react";
import { getProviders } from "../lib/rest";
import { useClickOutside } from "../lib/useClickOutside";
import type { ModelRow } from "../types/settings";
import { ChevronDownIcon } from "./icons";
import { ModelMarks } from "./ModelMarks";

/** One model the picker offers, `value` being "provider:model". */
interface Choice {
  provider: string;
  value: string;
  row: ModelRow;
}

interface ModelPickerProps {
  currentModel: string;
  onSwitch: (model: string) => void;
}

export function ModelPicker({ currentModel, onSwitch }: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [choices, setChoices] = useState<Choice[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);

  useEffect(() => {
    if (!open) return;
    // Re-fetched on every pill open, not cached -- a provider added
    // moments ago in Settings should show up here without a page reload.
    getProviders()
      .then((providers) =>
        setChoices(
          Object.entries(providers).flatMap(([provider, info]) =>
            info.models
              .filter((row) => row.kind === "chat")
              .map((row) => ({
                provider,
                value: `${provider}:${row.id}`,
                row,
              })),
          ),
        ),
      )
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (event.key < "1" || event.key > "9") return;
      const choice = choices[Number(event.key) - 1];
      if (!choice) return;
      event.preventDefault();
      const { value } = choice;
      setOpen(false);
      if (value !== currentModel) onSwitch(value);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, choices, currentModel, onSwitch]);

  const shortLabel = currentModel.includes(":") ? currentModel.split(":", 2)[1] : currentModel || "Select model";

  return (
    <div className="relative min-w-0 max-w-[9rem]" ref={rootRef}>
      <button
        type="button"
        data-testid="model-pill"
        className="flex h-8 max-w-full items-center gap-1 rounded-lg px-2 text-sm text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate">{shortLabel}</span>
        <ChevronDownIcon className="h-3.5 w-3.5 shrink-0" />
      </button>
      {open && (
        <div className="absolute bottom-full left-0 mb-1 max-h-96 w-72 overflow-y-auto rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] shadow-[var(--shadow)]">
          {choices.map(({ provider, value, row }, index) => {
            const isActive = value === currentModel;
            return (
              <div key={value}>
                {(index === 0 || choices[index - 1].provider !== provider) && <div className="px-3 pb-1 pt-2 text-xs text-[var(--muted)]">{provider}</div>}
                <div
                  className="flex cursor-pointer items-start justify-between gap-3 px-3 py-1.5 text-sm hover:bg-[var(--card-bg)]"
                  title={value}
                  onClick={() => {
                    setOpen(false);
                    if (value !== currentModel) onSwitch(value);
                  }}
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate">
                      {isActive ? "✓ " : ""}
                      {row.id}
                    </span>
                    <ModelMarks row={row} compact />
                  </span>
                  {index < 9 && <span className="text-xs text-[var(--muted)]">{index + 1}</span>}
                </div>
              </div>
            );
          })}
          {choices.length === 0 && <div className="px-3 py-2 text-sm text-[var(--muted)]">No models turned on. Add a provider in Settings.</div>}
        </div>
      )}
    </div>
  );
}
