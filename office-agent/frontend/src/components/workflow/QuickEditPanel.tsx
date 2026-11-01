import { type ReactNode, useState } from "react";
import { createPortal } from "react-dom";
import { inputClass, primaryButton, secondaryButton } from "../../lib/formStyles";
import { INPUT_TYPE_LABEL, isRelativeDate, resolveDate } from "../../lib/inputKinds";
import { plainDetail, plainKind } from "../../lib/plainSteps";
import { applyQuick, type QuickField, quickFields, replaceStep } from "../../lib/quickEdit";
import type { Workflow, WorkflowInput, WorkflowStep } from "../../types/workflow";
import { CloseIcon } from "../icons";
import { AutoTextarea, FieldLabel } from "./fields";
import { InputValueControl } from "./InputValueControl";

function ListField({ id, value, onChange }: { id: string; value: string[]; onChange: (next: string[]) => void }) {
  return (
    <>
      <AutoTextarea id={id} value={value.join("\n")} onChange={(text) => onChange(text.split("\n"))} />
      <p className="mt-1 text-xs text-[var(--muted)]">One per line.</p>
    </>
  );
}

function Field({ field, onChange }: { field: QuickField; onChange: (value: QuickField["value"]) => void }) {
  const id = `quick-${field.key}`;
  if (field.kind === "lock") {
    const on = field.value === true;
    return (
      <label className="flex cursor-pointer items-start gap-2 text-sm">
        <input type="checkbox" className="mt-0.5" checked={on} disabled={on} onChange={() => onChange(true)} />
        <span>
          {field.label}
          {field.hint && <span className="block text-xs text-[var(--muted)]">{field.hint}</span>}
        </span>
      </label>
    );
  }
  return (
    <div>
      <FieldLabel htmlFor={id} hint={field.hint}>
        {field.label}
      </FieldLabel>
      {field.kind === "shown" && <div className="text-sm text-[var(--muted)]">{String(field.value)}</div>}
      {field.kind === "text" && (
        <input id={id} className={inputClass} value={String(field.value)} onChange={(e) => onChange(e.target.value)} />
      )}
      {field.kind === "number" && (
        <input
          id={id}
          type="number"
          className={`${inputClass} max-w-[140px]`}
          value={String(field.value)}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
        />
      )}
      {field.kind === "longtext" && <AutoTextarea id={id} value={String(field.value)} onChange={onChange} />}
      {field.kind === "list" && <ListField id={id} value={field.value as string[]} onChange={onChange} />}
    </div>
  );
}

function tidy(step: WorkflowStep): WorkflowStep {
  // A list typed one per line keeps no blank lines.
  if (step.kind !== "agent") return step;
  const clean = (items: string[]) => items.map((item) => item.trim()).filter(Boolean);
  return { ...step, sites: clean(step.sites), folders: clean(step.folders) };
}

function QuickSheet({
  title,
  subtitle,
  children,
  error,
  canSave,
  onSave,
  onClose,
  onOpenEditor,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  error: string | null;
  canSave: boolean;
  onSave: () => void;
  onClose: () => void;
  onOpenEditor: () => void;
}) {
  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20" onClick={onClose}>
      <aside
        aria-label={title}
        className="flex h-full w-[min(420px,100vw)] flex-col border-l border-[var(--border)] bg-[var(--panel-bg)] shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-3.5">
          <div className="min-w-0">
            <h2 className="text-base font-semibold">{title}</h2>
            <div className="mt-0.5 text-[13px] text-[var(--muted)]">{subtitle}</div>
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-5 py-4">
          {children}
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        </div>
        <footer className="flex items-center justify-between gap-3 border-t border-[var(--border)] px-5 py-3">
          <button
            type="button"
            className="text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
            onClick={onOpenEditor}
          >
            Open in the full editor
          </button>
          <div className="flex gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>
              Cancel
            </button>
            <button type="button" className={primaryButton} disabled={!canSave} onClick={onSave}>
              Save
            </button>
          </div>
        </footer>
      </aside>
    </div>,
    document.body,
  );
}

/** Saves `next` and closes, or keeps the sheet open with the reason it couldn't. */
function useSave(persist: (next: Workflow) => Promise<string | null>, onClose: () => void) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const save = async (next: Workflow) => {
    setSaving(true);
    const problem = await persist(next);
    setSaving(false);
    if (problem) setError(problem);
    else onClose();
  };
  return { error, saving, save };
}

interface PanelProps {
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onClose: () => void;
  onOpenEditor: () => void;
}

/** Changes one step's fixed values from the simple view, without the full editor. */
export function QuickEditPanel({
  workflow,
  step,
  persist,
  onClose,
  onOpenEditor,
}: PanelProps & { step: WorkflowStep }) {
  const [draft, setDraft] = useState(step);
  const { error, saving, save } = useSave(persist, onClose);
  const detail = plainDetail(step, workflow.inputs);
  const changed = JSON.stringify(draft) !== JSON.stringify(step);
  return (
    <QuickSheet
      title="Change this step"
      subtitle={`${plainKind(step)}${detail ? ` · ${detail}` : ""}`}
      error={error}
      canSave={changed && !saving}
      onSave={() => void save(replaceStep(workflow, step.id, tidy(draft)))}
      onClose={onClose}
      onOpenEditor={onOpenEditor}
    >
      {quickFields(draft, workflow.inputs).map((field) => (
        <Field key={field.key} field={field} onChange={(value) => setDraft(applyQuick(draft, field.key, value))} />
      ))}
    </QuickSheet>
  );
}

/** Changes what an input is called and the value it usually has, from the simple view. */
export function InputQuickPanel({
  workflow,
  input,
  persist,
  onClose,
  onOpenEditor,
}: PanelProps & { input: WorkflowInput }) {
  const [draft, setDraft] = useState(input);
  const { error, saving, save } = useSave(persist, onClose);
  const changed = JSON.stringify(draft) !== JSON.stringify(input);
  const options = (draft.options ?? []).map((o) => o.trim()).filter(Boolean);
  const next = { ...draft, ...(draft.type === "choice" ? { options } : {}) };
  return (
    <QuickSheet
      title="Change what it asks for"
      subtitle={INPUT_TYPE_LABEL[input.type]}
      error={error}
      canSave={changed && !saving}
      onSave={() => void save({ ...workflow, inputs: workflow.inputs.map((i) => (i.name === input.name ? next : i)) })}
      onClose={onClose}
      onOpenEditor={onOpenEditor}
    >
      <div>
        <FieldLabel htmlFor="quick-input-label">Name</FieldLabel>
        <input
          id="quick-input-label"
          className={inputClass}
          value={draft.label}
          onChange={(e) => setDraft({ ...draft, label: e.target.value })}
        />
      </div>
      {draft.type === "choice" && (
        <div>
          <FieldLabel htmlFor="quick-input-options">Options</FieldLabel>
          <ListField
            id="quick-input-options"
            value={draft.options ?? []}
            onChange={(lines) => setDraft({ ...draft, options: lines })}
          />
        </div>
      )}
      <div>
        <FieldLabel
          hint={
            draft.type === "date" && isRelativeDate(draft.default)
              ? `${resolveDate(draft.default)} if it ran today`
              : undefined
          }
        >
          Usually
        </FieldLabel>
        <InputValueControl
          input={{ ...draft, options }}
          label="Usually"
          value={draft.default}
          onChange={(value) => setDraft({ ...draft, default: value === "" ? null : value })}
        />
      </div>
      <label className="flex cursor-pointer items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={draft.required === false}
          onChange={(e) => setDraft({ ...draft, required: !e.target.checked })}
        />
        <span>May be left blank</span>
      </label>
    </QuickSheet>
  );
}
