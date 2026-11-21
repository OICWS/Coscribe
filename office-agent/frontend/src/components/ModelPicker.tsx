import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { rememberModel, splitChoices, type ModelChoice } from "../lib/pickerModels";
import { getProviders } from "../lib/rest";
import { useClickOutside } from "../lib/useClickOutside";
import { CheckIcon, ChevronDownIcon, ChevronRightIcon } from "./icons";
import { ModelTip, type ModelTipAnchor } from "./ModelTip";

interface ModelPickerProps {
  currentModel: string;
  onSwitch: (model: string) => void;
}

const RECENT_KEY = "coscribe.recentModels";

function loadRecent(): string[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(stored) ? stored.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function saveRecent(recent: string[]) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
  } catch {
    // Without storage the menu falls back to the configured order.
  }
}

function choicesOf(providers: Awaited<ReturnType<typeof getProviders>>): ModelChoice[] {
  return Object.entries(providers).flatMap(([provider, info]) =>
    info.models.filter((row) => row.kind === "chat").map((row) => ({ provider, title: info.title, value: `${provider}:${row.id}`, row })),
  );
}

export function ModelPicker({ currentModel, onSwitch }: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [choices, setChoices] = useState<ModelChoice[]>([]);
  const [recent, setRecent] = useState<string[]>(loadRecent);
  const [tip, setTip] = useState<ModelTipAnchor | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const close = () => {
    setOpen(false);
    setMoreOpen(false);
    setTip(null);
  };
  useClickOutside(rootRef, close, open);

  useEffect(() => {
    if (!open) return;
    // Re-fetched on every pill open, not cached -- a provider added
    // moments ago in Settings should show up here without a page reload.
    getProviders()
      .then((providers) => setChoices(choicesOf(providers)))
      .catch(() => {});
  }, [open]);

  const { top, more } = splitChoices(choices, currentModel, recent);

  const pick = (value: string) => {
    close();
    const next = rememberModel(recent, value);
    setRecent(next);
    saveRecent(next);
    if (value !== currentModel) onSwitch(value);
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      const choice = top[Number(event.key) - 1];
      if (event.key < "1" || event.key > "9" || !choice) return;
      event.preventDefault();
      pick(choice.value);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  });

  const shortLabel = currentModel.includes(":") ? currentModel.split(":", 2)[1] : currentModel || "Select model";
  const row = (choice: ModelChoice, shortcut: number | null, side: "left" | "right" = "right") => (
    <ModelOption
      key={choice.value}
      choice={choice}
      active={choice.value === currentModel}
      shortcut={shortcut}
      onPick={() => pick(choice.value)}
      onHover={(e) => setTip({ rect: e.currentTarget.getBoundingClientRect(), row: choice.row, provider: choice.title, side })}
      onLeave={() => setTip(null)}
    />
  );

  return (
    <div className="relative min-w-0 max-w-[9rem]" ref={rootRef}>
      <button
        type="button"
        data-testid="model-pill"
        className="flex h-8 max-w-full items-center gap-1 rounded-lg px-2 text-sm text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span className="truncate">{shortLabel}</span>
        <ChevronDownIcon className="h-3.5 w-3.5 shrink-0" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-0 mb-1 w-64 rounded-[12px] border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]"
        >
          {top.map((choice, index) => row(choice, index + 1))}
          {choices.length === 0 && <div className="px-3 py-2 text-sm text-[var(--muted)]">No models turned on. Add a provider in Settings.</div>}
          {more.length > 0 && (
            <MoreModels open={moreOpen} onOpen={setMoreOpen}>
              {more.map((choice) => row(choice, null, "left"))}
            </MoreModels>
          )}
        </div>
      )}
      <ModelTip tip={open ? tip : null} />
    </div>
  );
}

/** The last row: the models beyond the first four, in a submenu that opens to the left. */
function MoreModels({ open, onOpen, children }: { open: boolean; onOpen: (open: boolean) => void; children: ReactNode }) {
  return (
    <div className="relative mt-1 border-t border-[var(--border)] pt-1" onMouseEnter={() => onOpen(true)} onMouseLeave={() => onOpen(false)}>
      <button
        type="button"
        className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-[var(--card-bg)] ${open ? "bg-[var(--card-bg)]" : ""}`}
        onClick={() => onOpen(!open)}
      >
        More models
        <ChevronRightIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
      </button>
      {open && (
        <div className="absolute bottom-0 right-full w-64 pr-1">
          <div className="max-h-80 overflow-y-auto rounded-[12px] border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

function ModelOption({
  choice,
  active,
  shortcut,
  onPick,
  onHover,
  onLeave,
}: {
  choice: ModelChoice;
  active: boolean;
  shortcut: number | null;
  onPick: () => void;
  onHover: (e: MouseEvent<HTMLButtonElement>) => void;
  onLeave: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--card-bg)]"
      onClick={onPick}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      <span className="truncate">{choice.row.name}</span>
      {active ? (
        <CheckIcon className="h-4 w-4 shrink-0 text-[var(--accent)]" />
      ) : (
        shortcut !== null && <span className="text-xs text-[var(--muted)]">{shortcut}</span>
      )}
    </button>
  );
}
