import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { createScheduledTask, patchScheduledTask } from "../lib/rest";
import type { Workflow } from "../types/workflow";
import type { ApprovalMode, ScheduledTask } from "../types/settings";
import type { TaskDraft } from "../types/wire";
import { CloseIcon } from "./icons";
import {
  fileInputs,
  initialSchedule,
  scheduleProblem,
  schedulePayload,
  webhookTaskId,
  type ScheduleForm,
} from "../lib/scheduleForm";
import { allSteps } from "../lib/workflowTree";
import { DEFAULT_ENVIRONMENT } from "./EnvironmentDialog";
import { EnvironmentPicker } from "./EnvironmentPicker";
import { FrequencyRow } from "./ScheduleFields";
import { SelectMenu } from "./SelectMenu";

const APPROVAL_OPTIONS: { value: ApprovalMode; label: string }[] = [
  { value: "manual", label: "Ask before every action" },
  { value: "auto", label: "Automatically approve" },
  { value: "skip", label: "Never ask" },
];

// No banner for "manual" -- it's the safe default, and no reference
// screenshot shows one for it (only "auto" does). "coscribe," not
// "Claude" -- this app's own product name, not a verbatim copy of the
// reference's own wording (that screenshot is Claude Cowork's own UI).
const APPROVAL_BANNER: Partial<Record<ApprovalMode, string>> = {
  auto: "For this task, Coscribe will create and edit files without asking, but pause before running code or using connectors.",
  skip: "For this task, Coscribe will never pause for approval -- it runs code and uses connectors on its own. Only your blocking rules still apply. Use with caution.",
};

const APPROVAL_VALUES = new Set<string>(APPROVAL_OPTIONS.map((o) => o.value));

/** The form's starting values: an existing task being edited, a draft the
 * model proposed (never trusted blindly -- anything the form can't
 * represent falls back to a default), or blank. */
function initialValues(task: ScheduledTask | null, draft: TaskDraft | undefined) {
  if (draft) {
    return {
      name: draft.name ?? "",
      instructions: draft.prompt ?? "",
      model: draft.model ?? "",
      approvalMode: (APPROVAL_VALUES.has(draft.approval_mode ?? "") ? draft.approval_mode : "manual") as ApprovalMode,
    };
  }
  return {
    name: task?.name ?? "",
    instructions: task?.prompt ?? "",
    model: task?.model ?? "",
    approvalMode: task?.approval_mode ?? "manual",
  };
}

interface ProviderInfo {
  default_model: string;
}

function modalTitle(isEdit: boolean, fromDraft: boolean, newWorkflow: Workflow | undefined): string {
  if (isEdit && fromDraft) return "Review changes";
  if (isEdit) return "Edit scheduled task";
  if (fromDraft) return "Review scheduled task";
  if (!newWorkflow) return "Create scheduled task";
  return newWorkflow.steps.length > 0 ? "Save workflow" : "Build a workflow";
}

function workflowSummary(workflow: Workflow, isEdit: boolean): string {
  const count = allSteps(workflow).length;
  if (count === 0) return "You'll add the workflow's steps on its page after saving.";
  const steps = count === 1 ? "1 step" : `${count} steps`;
  if (isEdit) return `This task runs a workflow of ${steps}. Edit its steps on the task page.`;
  return `Runs its ${steps}. Choose when it runs; you can keep editing the steps on its page.`;
}

interface ScheduledTaskModalProps {
  task: ScheduledTask | null; // null = create; otherwise editing this task
  /** Prefills a new task from what the model drafted in a conversation. */
  draft?: TaskDraft;
  onClose: () => void;
  onSaved: (task: ScheduledTask) => void;
  /** Create a task that runs this workflow (empty: steps are then built
   * on its page). */
  newWorkflow?: Workflow;
  initialName?: string;
  /** The environment runs use, when the task comes from a conversation: that conversation's. */
  initialEnvironment?: string | null;
  /** The conversation draft `newWorkflow` came from, and that conversation. */
  fromDraft?: string;
  fromThread?: string;
}

/** The Create/Edit scheduled task form; reachable
 * from RunPanel's "New task" menu, a task card/sidebar row's "Edit"
 * action, and the detail page's pencil icon (all pass a different `task`
 * prop into the same component rather than duplicating the form three
 * times). */
/** What the workflow task runs, and under it its environment, picked as under the message box. */
function WorkflowBox({ summary, environment, onPick }: { summary: string; environment: string; onPick: (id: string) => void }) {
  return (
    <div>
      <div className="rounded-md border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--muted)]">{summary}</div>
      <div className="-ml-0.5 flex items-center pt-1.5">
        <EnvironmentPicker current={environment} disabled={false} onPick={onPick} forTask />
      </div>
    </div>
  );
}

export function ScheduledTaskModal({
  task,
  draft,
  onClose,
  onSaved,
  newWorkflow,
  initialName,
  initialEnvironment,
  fromDraft,
  fromThread,
}: ScheduledTaskModalProps) {
  const isEdit = task !== null;
  const workflow = task?.workflow ?? newWorkflow ?? null;
  const [initial] = useState(() => ({ ...initialValues(task, draft), ...(initialName ? { name: initialName } : {}) }));
  const [name, setName] = useState(initial.name);
  const [instructions, setInstructions] = useState(initial.instructions);
  const [model, setModel] = useState(initial.model);
  const [environment, setEnvironment] = useState(task?.environment ?? initialEnvironment ?? DEFAULT_ENVIRONMENT);
  const [schedule, setSchedule] = useState<ScheduleForm>(() => initialSchedule(task, draft));
  const [approvalMode, setApprovalMode] = useState<ApprovalMode>(initial.approvalMode);
  const [providers, setProviders] = useState<[string, ProviderInfo][]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/providers")
      .then((res) => res.json())
      .then((data: Record<string, ProviderInfo>) => {
        setProviders(Object.entries(data).filter(([, info]) => info.default_model));
      })
      .catch(() => {});
  }, []);

  const save = async () => {
    const trimmedName = name.trim();
    const trimmedInstructions = instructions.trim();
    if (!trimmedName) {
      setError("Name is required.");
      return;
    }
    if (!trimmedInstructions && !workflow) {
      setError("Instructions are required.");
      return;
    }
    const missing = scheduleProblem(schedule);
    if (missing) return setError(missing);
    const payload = {
      name: trimmedName,
      ...schedulePayload(schedule, fileInputs(workflow)),
      prompt: trimmedInstructions,
      ...(model ? { model } : {}),
      approval_mode: approvalMode,
      notes_enabled: task?.notes_enabled ?? true,
      workflow,
      environment,
      ...(fromDraft ? { from_draft: fromDraft } : {}),
      ...(fromThread ? { from_thread: fromThread } : {}),
    };
    setSaving(true);
    setError(null);
    // An edit leaves the steps and notes to their own editors, which may
    // have saved since this form loaded.
    const { workflow: _steps, notes_enabled: _notes, ...formFields } = payload;
    const result = isEdit ? await patchScheduledTask(task.trigger_id, formFields) : await createScheduledTask(payload);
    setSaving(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    onSaved(result);
    onClose();
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-[min(720px,100vw-2rem)] flex-col rounded-[16px] border border-[var(--border)] bg-[var(--panel-bg)] p-6 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">{modalTitle(isEdit, Boolean(draft), newWorkflow)}</h2>
            {draft && (
              <p className="mt-0.5 text-sm text-[var(--muted)]">
                {isEdit
                  ? "Proposed in your conversation -- the task is unchanged until you save."
                  : "Drafted from your conversation -- adjust anything before saving."}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--border)] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
          <div>
            <label className="mb-1 block text-sm font-medium">
              Name <span className="text-[var(--danger)]">*</span>
            </label>
            <input
              className="w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
              placeholder="Daily briefing"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {workflow ? (
            <WorkflowBox summary={workflowSummary(workflow, isEdit)} environment={environment} onPick={setEnvironment} />
          ) : (
            <div>
              <label className="mb-1 block text-sm font-medium">
                Instructions <span className="text-[var(--danger)]">*</span>
              </label>
              <div className="overflow-hidden rounded-md border border-[var(--border)]">
                <textarea
                  className="w-full resize-none bg-transparent px-3 py-2 text-sm outline-none"
                  placeholder="Summarize my calendar and unread emails. Flag anything urgent."
                  rows={5}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                />
              </div>
              <div className="-ml-0.5 flex items-center justify-between pt-1.5 text-sm">
                <EnvironmentPicker current={environment} disabled={false} onPick={setEnvironment} forTask />
                <SelectMenu
                  ariaLabel="Model"
                  value={model}
                  options={[
                    { value: "", label: "Default model" },
                    ...providers.map(([providerKey, info]) => ({ value: `${providerKey}:${info.default_model}`, label: info.default_model })),
                  ]}
                  onChange={setModel}
                />
              </div>
            </div>
          )}

          <FrequencyRow form={schedule} onChange={setSchedule} workflow={workflow} taskId={webhookTaskId(task)} />

          {!workflow && (
            <div className="flex flex-wrap items-center gap-2">
              <label className="w-24 shrink-0 text-sm font-medium">Permissions</label>
              <SelectMenu ariaLabel="Permissions" variant="field" className="w-56" value={approvalMode} options={APPROVAL_OPTIONS} onChange={setApprovalMode} />
            </div>
          )}

          {!workflow && APPROVAL_BANNER[approvalMode] && (
            <div className="rounded-md border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)]">
              {APPROVAL_BANNER[approvalMode]}
            </div>
          )}

          {error && <div className="text-sm text-[var(--danger)]">{error}</div>}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            className="rounded-md border border-[var(--border)] px-4 py-1.5 text-sm hover:bg-[var(--card-bg)]"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            className="rounded-md bg-[var(--primary)] px-4 py-1.5 text-sm font-medium text-[var(--primary-fg)] disabled:opacity-60"
            onClick={save}
          >
            Save
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
