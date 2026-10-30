import { useEffect, useRef, useState } from "react";
import { asHexColour, type CanvasVariable } from "../../lib/designCanvas";
import { CloseIcon } from "../icons";

const FIELD = "h-8 min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] px-2 font-mono text-xs outline-none focus:border-[var(--accent)]";

/** One variable: a colour gets a swatch too. The text is set when it is left or Enter is pressed;
 * the swatch a moment after it stops changing, since dragging through colours fires many. */
function VariableRow({ variable, onSet }: { variable: CanvasVariable; onSet: (value: string) => void }) {
  const [typed, setTyped] = useState(variable.value);
  const [shown, setShown] = useState(variable.value);
  const timer = useRef<number | undefined>(undefined);
  // A new value from the file (coscribe rewrote it) replaces what was typed.
  if (shown !== variable.value) {
    setShown(variable.value);
    setTyped(variable.value);
  }
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const commit = (value: string) => {
    if (value.trim() && value.trim() !== variable.value) onSet(value.trim());
  };
  const hex = asHexColour(typed);
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-[var(--muted)]">{variable.label}</span>
      <span className="flex items-center gap-1.5">
        {hex && (
          <input
            type="color"
            aria-label={`${variable.label} colour`}
            className="h-8 w-9 shrink-0 cursor-pointer rounded-lg border border-[var(--border)] bg-transparent p-0.5"
            value={hex}
            onChange={(e) => {
              const value = e.target.value;
              setTyped(value);
              window.clearTimeout(timer.current);
              timer.current = window.setTimeout(() => commit(value), 300);
            }}
          />
        )}
        <input
          aria-label={variable.label}
          className={FIELD}
          value={typed}
          spellCheck={false}
          onChange={(e) => setTyped(e.target.value)}
          onBlur={() => commit(typed)}
          onKeyDown={(e) => e.key === "Enter" && commit(typed)}
        />
      </span>
    </label>
  );
}

/** The canvas's variables, which every artboard's page takes: its design system, edited in one place. */
export function CanvasVariables({ variables, onSet, onClose }: { variables: CanvasVariable[]; onSet: (name: string, value: string) => void; onClose: () => void }) {
  return (
    <div
      role="dialog"
      aria-label="Variables"
      className="absolute right-3 top-14 z-20 flex max-h-[calc(100%-4.5rem)] w-64 flex-col gap-3 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-3 shadow-[var(--shadow)]"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Variables</span>
        <button type="button" aria-label="Close variables" className="rounded-md p-1 hover:bg-[var(--card-bg)]" onClick={onClose}>
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
      {variables.map((variable) => (
        <VariableRow key={variable.name} variable={variable} onSet={(value) => onSet(variable.name, value)} />
      ))}
    </div>
  );
}
