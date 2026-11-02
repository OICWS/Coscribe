import { useState } from "react";
import type { StepRecord, WorkflowStep } from "../../types/workflow";
import { AgentCallRequest } from "./AgentActivity";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { AskCard, type AnswerValues, WaitCard } from "./PauseCards";

/** A step waiting for the person: an approval step, a folder or site the
 * run wasn't allowed, one call an agent step needs an OK for, or values an ask step needs; or a
 * wait step waiting for a time or a file. */
export function WaitingCard({
  step,
  record,
  onAnswer,
}: {
  step: WorkflowStep;
  record: StepRecord | undefined;
  onAnswer: (approved: boolean, note: string, values?: AnswerValues) => Promise<string | null>;
}) {
  const pause = record?.pause ?? null;
  // A wait goes on by itself: it isn't asking the person for anything.
  const tone = pause?.kind === "wait" ? "var(--kind-wait)" : "var(--warning)";
  return (
    <div
      className="flex flex-col gap-3 rounded-xl border px-4 py-3.5"
      style={{
        borderColor: `color-mix(in srgb, ${tone} 40%, transparent)`,
        backgroundColor: `color-mix(in srgb, ${tone} 7%, var(--bg))`,
      }}
    >
      <div className="flex flex-wrap items-baseline gap-x-2.5">
        <span className="text-sm font-medium">{step.title}</span>
        <span className="text-[13px] font-medium" style={{ color: tone }}>
          {pause?.kind === "wait" ? "Waiting" : "Waiting for you"}
        </span>
      </div>
      {pause?.kind === "ask" ? (
        <AskCard record={record} pause={pause} onAnswer={onAnswer} />
      ) : pause?.kind === "wait" ? (
        <WaitCard pause={pause} onAnswer={onAnswer} />
      ) : (
        <ApprovalBody step={step} record={record} onAnswer={onAnswer} />
      )}
    </div>
  );
}

/** An approval step, a folder or site the run wasn't allowed, or an agent's call. */
function ApprovalBody({
  step,
  record,
  onAnswer,
}: {
  step: WorkflowStep;
  record: StepRecord | undefined;
  onAnswer: (approved: boolean, note: string) => Promise<string | null>;
}) {
  const permission = record?.permission ?? null;
  const call = record?.agent?.pending;
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const answer = async (approved: boolean) => {
    setBusy(true);
    setError(await onAnswer(approved, note.trim()));
    setBusy(false);
  };
  return (
    <>
      {permission ? (
        <div className="flex flex-col gap-1" data-testid="permission-request">
          <p className="text-sm font-medium">
            {permission.kind === "folder"
              ? "It needs to change a folder it hasn’t been allowed"
              : "It needs to open a website it hasn’t been allowed"}
          </p>
          <p className="break-all text-sm">{permission.target}</p>
          <p className="text-[13px] text-[var(--muted)]">
            {permission.kind === "folder"
              ? "Allowing adds it to this workflow for this and later runs. The step then runs again from its start."
              : "Allowing adds it to this workflow for this and later runs."}
          </p>
        </div>
      ) : (
        <>
          {call && <AgentCallRequest call={call} step={step} />}
          {!call && typeof record?.output === "string" && (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{record.output}</p>
          )}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-[var(--muted)]">
              {call ? "Note (optional, the agent reads it if you don’t allow)" : "Note (optional, saved with this run)"}
            </span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm outline-none hover:border-[var(--border-hover)] focus:border-[var(--border-hover)]"
            />
          </label>
        </>
      )}
      <div className="flex gap-2">
        <button type="button" disabled={busy} className={primaryButton} onClick={() => answer(true)}>
          {permission || call ? "Allow and continue" : "Approve and continue"}
        </button>
        <button type="button" disabled={busy} className={secondaryButton} onClick={() => answer(false)}>
          {permission || call ? "Don’t allow" : "Decline"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-[13px] text-[var(--danger)]">
          {error}
        </p>
      )}
    </>
  );
}
