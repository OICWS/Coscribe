import { useState } from "react";
import { placeSteps } from "../../lib/workflowTree";
import type { WorkflowStep } from "../../types/workflow";

// Past this many, a nested list shows its first steps and a "more" button, so a long loop body
// doesn't push the rest of the task out of view.
const SHOWN_FIRST = 4;
const COLLAPSE_OVER = 6;

function Tag({ children, tone = "muted" }: { children: string; tone?: "muted" | "warning" }) {
  const color =
    tone === "warning"
      ? "bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[var(--fg)]"
      : "bg-[var(--card-bg)] text-[var(--muted)]";
  return <span className={`ml-2 rounded-full px-1.5 py-0.5 text-[11px] font-medium ${color}`}>{children}</span>;
}

/** What a person needs to know about a step beyond its title: who does it, and whether it waits
 * for them or can't be taken back. How it does it is the detailed view's. */
function tags(step: WorkflowStep) {
  return (
    <>
      {(step.kind === "agent" || step.kind === "llm") && <Tag>AI</Tag>}
      {step.kind === "approval" && <Tag tone="warning">Waits for your OK</Tag>}
      {step.kind === "check" && <Tag>Check</Tag>}
      {cannotUndo(step) && <Tag tone="warning">Can’t be undone</Tag>}
    </>
  );
}

function cannotUndo(step: WorkflowStep): boolean {
  return (step.kind === "tool" || step.kind === "agent") && step.irreversible;
}

function Nested({ label, steps }: { label: string; steps: WorkflowStep[] }) {
  if (steps.length === 0) return null;
  return (
    <div className="mt-1.5">
      <div className="text-[13px] text-[var(--muted)]">{label}</div>
      <StepList steps={steps} nested />
    </div>
  );
}

function StepItem({ step }: { step: WorkflowStep }) {
  return (
    <li className="pl-1">
      <span>{step.title}</span>
      {tags(step)}
      {step.kind === "loop" && <Nested label="For each one:" steps={step.steps} />}
      {step.kind === "branch" && (
        <>
          <Nested label="If so:" steps={step.then} />
          <Nested label="Otherwise:" steps={step.otherwise} />
        </>
      )}
    </li>
  );
}

function StepList({ steps, nested = false }: { steps: WorkflowStep[]; nested?: boolean }) {
  const [open, setOpen] = useState(false);
  const collapsed = nested && !open && steps.length > COLLAPSE_OVER;
  const shown = collapsed ? steps.slice(0, SHOWN_FIRST) : steps;
  // A step that can't be taken back is never hidden without saying so.
  const hiddenFinal = collapsed
    ? placeSteps(steps.slice(SHOWN_FIRST)).filter((placed) => cannotUndo(placed.step)).length
    : 0;
  return (
    <ol
      className={`list-decimal space-y-1.5 text-sm marker:text-[var(--muted)] ${
        nested ? "ml-1 mt-1 border-l border-[var(--border)] pl-6" : "pl-6"
      }`}
    >
      {shown.map((step) => (
        <StepItem key={step.id} step={step} />
      ))}
      {collapsed && (
        <li className="list-none">
          <button
            type="button"
            className="text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
            onClick={() => setOpen(true)}
          >
            {steps.length - SHOWN_FIRST} more steps
            {hiddenFinal > 0 && `, ${hiddenFinal} of them can’t be undone`}
          </button>
        </li>
      )}
    </ol>
  );
}

/** A workflow's steps as a numbered list of their titles, for someone who reads it rather than
 * builds it: loops and branches indent what they hold, and no step shows a tool, a script or a
 * variable name. */
export function StepOutline({ steps }: { steps: WorkflowStep[] }) {
  return <StepList steps={steps} />;
}
