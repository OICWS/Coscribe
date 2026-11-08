import type { ReactNode } from "react";
import { type PlainGroup, type PlainRow, plainOutline } from "../../lib/plainOutline";
import { plainKind } from "../../lib/plainSteps";
import { useTaskNames } from "../../lib/taskCalls";
import type { Workflow, WorkflowInput } from "../../types/workflow";
import { PlainTile, plainColor } from "./WorkflowCanvas";

/** A sentence with each input it reads as a chip, so what the person fills in stands out from
 * what the task works out. */
export function PlainText({ text, inputs }: { text: string; inputs: WorkflowInput[] }) {
  const labels = new Set(inputs.map((input) => input.label || input.name));
  // A reference inside quoted text is "[Label]"; a whole one is "“Label”".
  const parts = text.split(/(\[[^\]]+\]|“[^”]+”)/);
  return (
    <>
      {parts.map((part, index) => {
        const inner = part.slice(1, -1);
        if (/^(\[.+\]|“.+”)$/.test(part) && labels.has(inner))
          return (
            <span
              key={index}
              className="mx-px rounded border border-[var(--border)] bg-[var(--card-bg)] px-1 py-px text-[12px] text-[var(--fg)]"
            >
              {inner}
            </span>
          );
        // Quoted text holding a chip: its quotes stay, its inside is split again.
        if (part.startsWith("“") && /\[[^\]]+\]/.test(part))
          return (
            <span key={index}>
              “<PlainText text={inner} inputs={inputs} />”
            </span>
          );
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

function Row({
  row,
  number,
  inputs,
  onOpen,
  openId,
}: {
  row: PlainRow;
  number: number | null;
  inputs: WorkflowInput[];
  onOpen: (stepId: string) => void;
  openId: string | null;
}): ReactNode {
  const { step } = row;
  return (
    <li>
      <button
        type="button"
        data-testid="plain-step"
        data-plain-step={step.id}
        aria-current={openId === step.id ? "true" : undefined}
        className="group flex w-full items-start gap-3 rounded-md px-2 py-2 text-left hover:bg-[var(--card-bg)] aria-[current]:bg-[var(--card-bg)]"
        onClick={() => onOpen(step.id)}
      >
        {number !== null ? (
          <span className="mt-px w-5 shrink-0 text-right text-[13px] tabular-nums text-[var(--muted)]">{number}</span>
        ) : null}
        <PlainTile step={step} color={plainColor(step)} />
        <span className="min-w-0 flex-1">
          <span className="block text-sm leading-snug">{step.title}</span>
          {row.detail && (
            <span className="mt-0.5 block text-[13px] leading-snug text-[var(--muted)] [overflow-wrap:anywhere]">
              <PlainText text={row.detail} inputs={inputs} />
            </span>
          )}
          {row.notes.length > 0 && (
            <span className="mt-1 flex flex-wrap gap-1">
              {row.notes.map((note) => (
                <span
                  key={note}
                  className={`rounded-full px-1.5 py-0.5 text-[11px] font-medium ${
                    note === "Can’t be undone"
                      ? "bg-[color-mix(in_srgb,var(--warning)_18%,transparent)]"
                      : "bg-[var(--card-bg)] text-[var(--muted)]"
                  }`}
                >
                  {note}
                </span>
              ))}
            </span>
          )}
        </span>
        <span className="mt-px shrink-0 text-xs text-[var(--muted)]">{plainKind(step)}</span>
      </button>
      {row.groups.map((group, index) => (
        <Group key={index} group={group} inputs={inputs} onOpen={onOpen} openId={openId} indent={number !== null} />
      ))}
    </li>
  );
}

function Group({
  group,
  inputs,
  onOpen,
  openId,
  indent,
}: {
  group: PlainGroup;
  inputs: WorkflowInput[];
  onOpen: (stepId: string) => void;
  openId: string | null;
  indent: boolean;
}) {
  return (
    <div className={`${indent ? "ml-9" : "ml-6"} border-l border-[var(--border)] pl-2`}>
      {group.label && <div className="px-2 pt-1.5 text-xs font-medium text-[var(--muted)]">{group.label}</div>}
      <ul>
        {group.rows.map((row) => (
          <Row key={row.step.id} row={row} number={null} inputs={inputs} onOpen={onOpen} openId={openId} />
        ))}
      </ul>
    </div>
  );
}

/** What a task does, one plain sentence per step, numbered at the top level; a block's steps sit
 * under the words that say when they run. A step opens its quick edit. */
export function PlainStepList({
  workflow,
  onOpenStep,
  openStepId,
}: {
  workflow: Workflow;
  onOpenStep: (stepId: string) => void;
  openStepId: string | null;
}) {
  const outline = plainOutline(workflow, useTaskNames());
  if (outline.length === 0) return <p className="text-sm text-[var(--muted)]">No steps yet.</p>;
  return (
    <ol className="-mx-2 flex flex-col" data-testid="plain-step-list">
      {outline.map((row, index) => (
        <Row
          key={row.step.id}
          row={row}
          number={index + 1}
          inputs={workflow.inputs}
          onOpen={onOpenStep}
          openId={openStepId}
        />
      ))}
    </ol>
  );
}
