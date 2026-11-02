import { Fragment, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { dataFlow, flowRole, type FlowRole, type StepFlow } from "../../lib/dataFlow";
import { failureLine } from "../../lib/failureWords";
import { AUTONOMY_LABEL, KIND_COLOR, KIND_LABEL } from "../../lib/workflowLabels";
import { plainDetail, plainKind } from "../../lib/plainSteps";
import { type NodeRunState, runMap } from "../../lib/workflowRunMap";
import { canRecover, everyStep, isBlock, placeSteps } from "../../lib/workflowTree";
import type { ScheduledRun } from "../../types/settings";
import type {
  BranchStep,
  ChoiceStep,
  LoopStep,
  RecoveringStep,
  Workflow,
  WorkflowInput,
  WorkflowStep,
} from "../../types/workflow";
import { FileTextIcon, GlobeIcon, LoopIcon, RetryIcon, TerminalIcon } from "../icons";
import { StepKindTile, VarToken } from "./parts";
import { StatusDot } from "./StatusDot";
import { StepSummary } from "./StepSummary";

// The diagram is laid out by the workflow's own structure (a list runs top
// to bottom, a branch's arms side by side, a loop's body inside a frame), so
// it needs no graph layout engine and can't come out in an order the engine
// wouldn't run.

interface CanvasContext {
  numbers: Map<string, number>;
  inputNames: Set<string>;
  /** Each step's state when the canvas shows a run. */
  states?: Map<string, NodeRunState>;
  onOpenStep?: (stepId: string) => void;
  /** The simple view: each step says what it does in plain words, without tool or variable names. */
  plain?: { inputs: WorkflowInput[] };
  /** Inside a split of three or more paths, where full-width cards would push the rest off the page. */
  narrow?: boolean;
  /** Which steps feed and use the one in focus (pointed at or opened), to light up its data. */
  flow: { flows: Map<string, StepFlow>; focus: string | null; setFocus: (id: string | null) => void };
}

const FAIL_COLOR = "var(--danger)";

const ROLE: Record<Exclude<FlowRole, "focus" | "other">, { label: string; color: string }> = {
  feeds: { label: "Gives it values", color: "var(--kind-script)" },
  uses: { label: "Uses its result", color: "var(--kind-check)" },
  both: { label: "Gives and uses", color: "var(--kind-script)" },
};

function RoleTag({ role }: { role: FlowRole }) {
  if (role === "focus" || role === "other") return null;
  const { label, color } = ROLE[role];
  return (
    <span
      className="rounded-full px-1.5 py-px text-[11px] font-medium"
      style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
    >
      {label}
    </span>
  );
}

function FailureNote({ step }: { step: WorkflowStep }) {
  const line = failureLine(step);
  if (!line) return null;
  return (
    <span className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
      <RetryIcon className="h-3 w-3 shrink-0" style={{ color: FAIL_COLOR }} />
      {line}
    </span>
  );
}

const LINE = "bg-[var(--border-hover)]";

function Arrow() {
  return (
    <div aria-hidden="true" className="flex flex-col items-center">
      <div className={`h-4 w-px ${LINE}`} />
      <svg width="9" height="6" viewBox="0 0 9 6" className="text-[var(--border-hover)]">
        <path d="M0 0h9L4.5 6z" fill="currentColor" />
      </svg>
    </div>
  );
}

function Terminal({ faded = false, children }: { faded?: boolean; children: ReactNode }) {
  return (
    <div
      className={`${faded ? "opacity-55 " : ""}flex max-w-80 flex-wrap items-baseline justify-center gap-x-1.5 gap-y-1 rounded-full border border-[var(--border)] bg-[var(--bg)] px-3.5 py-1.5 text-xs text-[var(--muted)] shadow-sm`}
    >
      {children}
    </div>
  );
}

const RUN_TEXT: Partial<Record<NodeRunState["status"], string>> = {
  running: "Running…",
  waiting: "Waiting for you",
  failed: "Failed here",
  stopped: "Stopped here",
  skipped: "Skipped",
  not_taken: "Not taken",
  pending: "Up next",
};

const RECOVERED: Record<NonNullable<NodeRunState["recovered"]>, string> = {
  skipped: "Failed, skipped it",
  fallback: "Failed, ran the steps in its place",
  item_skipped: "Failed, skipped the item",
};

function loopText(state: NodeRunState, done: number, total: number | null, skipped: number): string {
  const of = total === null ? "" : ` of ${total}`;
  const also = skipped > 0 ? ` · ${skipped} skipped` : "";
  if (state.status === "failed" || state.status === "stopped") return `Stopped at item ${done + 1}${of}`;
  if (state.status === "waiting") return `Waiting at item ${done + 1}${of}`;
  const through = `${done}${of} ${(total ?? done) === 1 ? "item" : "items"} through${also}`;
  return state.status === "running" ? `Running… · ${through}` : through;
}

function runText(step: WorkflowStep, state: NodeRunState): string | null {
  const { passes } = state;
  const tries = state.attempts ? `worked on try ${state.attempts}` : null;
  const lead =
    state.status === "recovered" && state.recovered
      ? RECOVERED[state.recovered]
      : state.status === "done" && tries
        ? tries.charAt(0).toUpperCase() + tries.slice(1)
        : (RUN_TEXT[state.status] ?? null);
  if (passes && (state.status !== "not_reached" || passes.done > 0)) {
    if (step.kind === "loop") return loopText(state, passes.done, passes.total, passes.skipped ?? 0);
    // A step inside a loop: how many items it has been done for so far.
    const count = passes.total === null ? `${passes.done}` : `${passes.done} of ${passes.total}`;
    const items = `${count} ${(passes.total ?? passes.done) === 1 ? "item" : "items"}`;
    if (!lead || state.status === "skipped") return `Done for ${items}`;
    return passes.done > 0 ? `${lead} · done for ${items}` : lead;
  }
  if ((step.kind === "branch" || step.kind === "choice") && state.arms?.length) {
    const label = (arm: string) => armsOf(step, false).find(([a]) => a === arm)?.[1] ?? arm;
    return `Took ${state.arms.map(label).join(" and ")}`;
  }
  return lead;
}

// How a node looks for its state: a ring where the run needs attention or
// is working, faded where it hasn't been or won't be.
function runLook(state: NodeRunState | undefined): { className: string; ring?: string } {
  if (!state) return { className: "" };
  if (state.status === "failed") return { className: "", ring: "var(--danger)" };
  if (state.status === "waiting") return { className: "", ring: "var(--warning)" };
  if (state.status === "running") return { className: "", ring: "var(--accent)" };
  if (state.status === "recovered") return { className: "", ring: "var(--warning)" };
  if (state.status === "not_reached" || state.status === "not_taken" || state.status === "skipped") {
    return { className: "opacity-55" };
  }
  return { className: "" };
}

function cannotUndo(step: WorkflowStep): boolean {
  return (step.kind === "tool" || step.kind === "agent") && step.irreversible;
}

/** A step for someone who reads the task rather than builds it: what kind of thing it is, its
 * title, and one sentence on what it does. */
// The simple view colours a step by what a person sees it touch; a program is background work,
// so it takes the quiet colour.
function plainColor(step: WorkflowStep): string {
  if (step.kind === "script") return KIND_COLOR.tool;
  if (step.kind !== "tool") return KIND_COLOR[step.kind];
  if (step.tool.startsWith("browser_")) return "var(--kind-web)";
  return plainKind(step) === "File" ? "var(--kind-file)" : KIND_COLOR.tool;
}

function PlainTile({ step, color }: { step: WorkflowStep; color: string }) {
  const web = step.kind === "tool" && step.tool.startsWith("browser_");
  const file = step.kind === "tool" && plainKind(step) === "File";
  if (!web && !file && step.kind !== "script") return <StepKindTile step={step} size="sm" />;
  const Glyph = web ? GlobeIcon : file ? FileTextIcon : TerminalIcon;
  return (
    <span
      aria-hidden="true"
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md"
      style={{ color, backgroundColor: `color-mix(in srgb, ${color} 13%, transparent)` }}
    >
      <Glyph className="h-3 w-3" />
    </span>
  );
}

function PlainBody({
  step,
  inputs,
  state,
  role,
}: {
  step: WorkflowStep;
  inputs: WorkflowInput[];
  state?: NodeRunState;
  role: FlowRole;
}) {
  const color = plainColor(step);
  const detail = plainDetail(step, inputs);
  return (
    <>
      <span className="flex items-center gap-2">
        <PlainTile step={step} color={color} />
        <span
          className="rounded-full px-2 py-px text-[11px] font-medium"
          style={{ color, backgroundColor: `color-mix(in srgb, ${color} 10%, transparent)` }}
        >
          {plainKind(step)}
        </span>
        <span className="ml-auto flex items-center gap-1">
          <RoleTag role={role} />
          {cannotUndo(step) && (
            <span className="rounded-full bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] px-1.5 py-0.5 text-[11px] font-medium">
              Can’t be undone
            </span>
          )}
        </span>
        {state && <StatusDot status={state.status} />}
      </span>
      <span className="mt-1.5 line-clamp-2 block text-sm font-medium leading-snug" title={step.title}>
        {step.title}
      </span>
      {detail && <span className="mt-1 line-clamp-2 block text-xs text-[var(--muted)]">{detail}</span>}
    </>
  );
}

function StepNode({ step, ctx }: { step: WorkflowStep; ctx: CanvasContext }) {
  const color = KIND_COLOR[step.kind];
  const state = ctx.states?.get(step.id);
  const note = state ? runText(step, state) : null;
  const look = runLook(state);
  const { flows, focus, setFocus } = ctx.flow;
  const role = focus ? flowRole(flows, focus, step.id) : "focus";
  const kind = step.kind === "agent" ? `Agent · ${AUTONOMY_LABEL[step.autonomy]}` : KIND_LABEL[step.kind];
  const body = ctx.plain ? (
    <>
      <PlainBody step={step} inputs={ctx.plain.inputs} state={state} role={role} />
      <FailureNote step={step} />
      {note && (
        <span
          className="mt-1.5 block border-t border-[var(--border)] pt-1.5 text-xs font-medium"
          style={{ color: look.ring }}
        >
          {note}
        </span>
      )}
    </>
  ) : (
    <>
      <span className="flex items-center gap-2">
        <StepKindTile step={step} size="sm" />
        <span className="text-[11px] font-medium uppercase tracking-[0.06em]" style={{ color }}>
          {kind}
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <RoleTag role={role} />
          <span className="text-xs tabular-nums text-[var(--muted)]">{ctx.numbers.get(step.id)}</span>
        </span>
        {state && <StatusDot status={state.status} />}
      </span>
      <span className="mt-1.5 line-clamp-2 block text-[13px] font-medium leading-snug" title={step.title}>
        {step.title}
      </span>
      <span className="mt-1 flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-xs text-[var(--muted)]">
        <StepSummary step={step} inputNames={ctx.inputNames} />
      </span>
      <FailureNote step={step} />
      {note && (
        <span
          className="mt-1.5 block border-t border-[var(--border)] pt-1.5 text-xs font-medium"
          style={{ color: look.ring }}
        >
          {note}
        </span>
      )}
    </>
  );
  const dim = role === "other" ? "opacity-40" : "";
  const className = `block ${ctx.narrow ? "w-48" : "w-64"} rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 pb-2.5 pt-2 text-left shadow-sm transition-opacity ${look.className} ${dim}`;
  const ring =
    look.ring ??
    (role === "focus" && focus
      ? "var(--accent)"
      : role !== "other" && focus
        ? ROLE[role as keyof typeof ROLE].color
        : undefined);
  const style = {
    borderTopColor: ctx.plain ? plainColor(step) : color,
    borderTopWidth: 3,
    ...(ring ? { boxShadow: `0 0 0 2px color-mix(in srgb, ${ring} 45%, transparent)` } : {}),
  };
  const pointer = {
    onMouseEnter: () => setFocus(step.id),
    onMouseLeave: () => setFocus(null),
    onFocus: () => setFocus(step.id),
    onBlur: () => setFocus(null),
  };
  if (!ctx.onOpenStep) {
    return (
      <div className={className} style={style} data-canvas-step={step.id} data-run-status={state?.status} {...pointer}>
        {body}
      </div>
    );
  }
  return (
    <button
      type="button"
      className={`${className} transition-colors hover:border-[var(--border-hover)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]`}
      style={style}
      data-canvas-step={step.id}
      data-run-status={state?.status}
      data-flow-role={focus ? role : undefined}
      title={ctx.states ? `Show "${step.title}" in the run` : `Edit "${step.title}"`}
      onClick={() => ctx.onOpenStep?.(step.id)}
      {...pointer}
    >
      {body}
    </button>
  );
}

function ArmLabel({
  taken,
  color = KIND_COLOR.branch,
  children,
}: {
  taken: boolean;
  color?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={`rounded-full border px-2 py-px text-[11px] ${taken ? "font-medium" : "border-[var(--border)] bg-[var(--card-bg)] text-[var(--muted)]"}`}
      style={
        taken
          ? { color, borderColor: color, backgroundColor: `color-mix(in srgb, ${color} 10%, transparent)` }
          : undefined
      }
    >
      {children}
    </span>
  );
}

function armsOf(step: BranchStep | ChoiceStep, plain: boolean): [string, string, WorkflowStep[]][] {
  if (step.kind === "branch") {
    return [
      ["then", plain ? "If so" : "Then", step.then],
      ["otherwise", plain ? "If not" : "Otherwise", step.otherwise],
    ];
  }
  return [
    ...step.cases.map((c, i): [string, string, WorkflowStep[]] => [`case:${i}`, `“${c.is}”`, c.steps]),
    ["otherwise", plain ? "Anything else" : "Otherwise", step.otherwise],
  ];
}

/** Where an arm's share of the split and join lines runs: from its middle outward, or across. */
function lineSpan(index: number, count: number): string {
  if (index === 0) return "left-1/2 right-0";
  return index === count - 1 ? "left-0 right-1/2" : "left-0 right-0";
}

// Past this many paths side by side, the split no longer fits a page, so the paths stack.
const SIDE_BY_SIDE = 3;

/** Many paths, one under another in a frame that says only one of them runs. */
function StackedPaths({ step, ctx }: { step: ChoiceStep; ctx: CanvasContext }) {
  const arms = armsOf(step, Boolean(ctx.plain));
  const taken = ctx.states?.get(step.id)?.arms ?? [];
  const color = KIND_COLOR.choice;
  return (
    <div className="flex flex-col items-center">
      <StepNode step={step} ctx={ctx} />
      <Arrow />
      <div
        className="flex flex-col items-center rounded-2xl border border-dashed px-5 pb-4 pt-2.5"
        style={{
          borderColor: `color-mix(in srgb, ${color} 55%, transparent)`,
          backgroundColor: `color-mix(in srgb, ${color} 4%, transparent)`,
        }}
      >
        <span className="mb-1 text-xs font-medium" style={{ color }}>
          Only one of these {arms.length} paths runs
        </span>
        {arms.map(([arm, label, steps], index) => (
          <div
            key={arm}
            className={`flex flex-col items-center pt-3 ${index > 0 ? "mt-3 border-t border-dashed border-[var(--border)]" : ""}`}
          >
            <ArmLabel taken={taken.includes(arm)}>{label}</ArmLabel>
            {steps.length > 0 ? (
              <>
                <Arrow />
                <Flow steps={steps} ctx={ctx} />
              </>
            ) : (
              <span className="mt-2 text-xs italic text-[var(--muted)]">nothing</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function BranchBlock({ step, ctx }: { step: BranchStep | ChoiceStep; ctx: CanvasContext }) {
  const arms = armsOf(step, Boolean(ctx.plain));
  const taken = ctx.states?.get(step.id)?.arms ?? [];
  if (step.kind === "choice" && arms.length > SIDE_BY_SIDE) return <StackedPaths step={step} ctx={ctx} />;
  const inner = arms.length > 2 ? { ...ctx, narrow: true } : ctx;
  return (
    <div className="flex flex-col items-center">
      <StepNode step={step} ctx={ctx} />
      <div aria-hidden="true" className={`h-4 w-px ${LINE}`} />
      <div className="flex">
        {arms.map(([arm, label, steps], index) => (
          <div key={arm} className={`relative flex flex-col items-center ${inner.narrow ? "px-2.5" : "px-4"}`}>
            {/* Each arm draws the half of the split and join lines on its own
                side, so they meet whatever width each arm needs. */}
            <div aria-hidden="true" className={`absolute top-0 h-px ${lineSpan(index, arms.length)} ${LINE}`} />
            <div aria-hidden="true" className={`absolute bottom-0 h-px ${lineSpan(index, arms.length)} ${LINE}`} />
            <div aria-hidden="true" className={`h-3 w-px ${LINE}`} />
            <ArmLabel taken={taken.includes(arm)}>{label}</ArmLabel>
            {steps.length > 0 ? (
              <>
                <Arrow />
                <Flow steps={steps} ctx={inner} />
              </>
            ) : (
              <span className="mt-2 text-xs italic text-[var(--muted)]">nothing</span>
            )}
            <div aria-hidden="true" className={`min-h-4 w-px flex-1 ${LINE}`} />
          </div>
        ))}
      </div>
    </div>
  );
}

/** A step with steps to run in its place when it fails: the main line goes on from it, and the
 * steps in its place sit beside it and rejoin the line after. */
function RecoverBlock({ step, ctx }: { step: RecoveringStep; ctx: CanvasContext }) {
  const inPlace = step.on_failure?.steps ?? [];
  const taken = ctx.states?.get(step.id)?.arms ?? [];
  const arm = (index: number, label: ReactNode, inside: ReactNode) => (
    <div className="relative flex flex-col items-center px-4">
      <div aria-hidden="true" className={`absolute top-0 h-px ${lineSpan(index, 2)} ${LINE}`} />
      <div aria-hidden="true" className={`absolute bottom-0 h-px ${lineSpan(index, 2)} ${LINE}`} />
      <div aria-hidden="true" className={`h-3 w-px ${LINE}`} />
      {label}
      {inside}
      <div aria-hidden="true" className={`min-h-4 w-px flex-1 ${LINE}`} />
    </div>
  );
  return (
    <div className="flex flex-col items-center">
      <StepNode step={step} ctx={ctx} />
      <div aria-hidden="true" className={`h-4 w-px ${LINE}`} />
      <div className="flex">
        {arm(0, <ArmLabel taken={false}>If it works</ArmLabel>, null)}
        {arm(
          1,
          <ArmLabel taken={taken.includes("fallback")} color={FAIL_COLOR}>
            If it fails
          </ArmLabel>,
          inPlace.length > 0 ? (
            <>
              <Arrow />
              <Flow steps={inPlace} ctx={ctx} />
            </>
          ) : (
            <span className="mt-2 text-xs italic text-[var(--muted)]">no steps yet</span>
          ),
        )}
      </div>
    </div>
  );
}

/** What runs when a run fails, apart from the main line: nothing leads into it but a failure. */
function AfterFailure({ steps, ctx }: { steps: WorkflowStep[]; ctx: CanvasContext }) {
  return (
    <div
      data-testid="after-failure"
      className="mt-8 flex flex-col items-center rounded-2xl border border-dashed px-5 pb-5 pt-3"
      style={{
        borderColor: `color-mix(in srgb, ${FAIL_COLOR} 45%, transparent)`,
        backgroundColor: `color-mix(in srgb, ${FAIL_COLOR} 3%, transparent)`,
      }}
    >
      <span className="text-xs font-medium" style={{ color: FAIL_COLOR }}>
        If a run fails
      </span>
      <span className="mb-1 text-[11px] text-[var(--muted)]">Then these run, and the run still counts as failed</span>
      <Arrow />
      <Flow steps={steps} ctx={ctx} />
    </div>
  );
}

/** The simple view names a loop once, on its frame: its title, then what it repeats for. */
function PlainLoopHeader({ step, ctx }: { step: LoopStep; ctx: CanvasContext }) {
  const color = KIND_COLOR.loop;
  return (
    <button
      type="button"
      disabled={!ctx.onOpenStep}
      data-canvas-step={step.id}
      className={`mb-1 flex ${ctx.narrow ? "w-48" : "w-64"} items-start gap-2 rounded-lg px-1 py-0.5 text-left enabled:hover:bg-[var(--card-bg)]`}
      onClick={() => ctx.onOpenStep?.(step.id)}
    >
      <LoopIcon className="mt-0.5 h-4 w-4 shrink-0" style={{ color }} />
      <span className="min-w-0">
        <span className="block text-sm font-medium">{step.title}</span>
        <span className="block text-xs" style={{ color }}>
          Repeats for each {step.item.replace(/_/g, " ")}, up to {step.max_items}
        </span>
        {step.on_item_failure === "skip" && (
          <span className="mt-0.5 flex items-center gap-1 text-[11px] text-[var(--muted)]">
            <RetryIcon className="h-3 w-3" style={{ color: FAIL_COLOR }} />
            An item that fails is skipped and listed in the report
          </span>
        )}
      </span>
    </button>
  );
}

// A long loop body shows its first steps and a button for the rest, so one loop doesn't fill
// the page.
const SHOWN_FIRST = 3;
const COLLAPSE_OVER = 5;

function ShortFlow({ steps, ctx }: { steps: WorkflowStep[]; ctx: CanvasContext }) {
  const [open, setOpen] = useState(false);
  if (open || steps.length <= COLLAPSE_OVER) return <Flow steps={steps} ctx={ctx} />;
  const hidden = steps.slice(SHOWN_FIRST);
  // A step that can't be taken back is never hidden without saying so.
  const final = placeSteps(hidden).filter((placed) => cannotUndo(placed.step)).length;
  return (
    <div className="flex flex-col items-center">
      <Flow steps={steps.slice(0, SHOWN_FIRST)} ctx={ctx} />
      <Arrow />
      <button
        type="button"
        className="rounded-full border border-[var(--border)] bg-[var(--bg)] px-3.5 py-1.5 text-xs text-[var(--muted)] shadow-sm hover:text-[var(--fg)]"
        onClick={() => setOpen(true)}
      >
        {hidden.length} more steps{final > 0 && `, ${final} can’t be undone`}
      </button>
    </div>
  );
}

function LoopBlock({ step, ctx }: { step: LoopStep; ctx: CanvasContext }) {
  const color = KIND_COLOR.loop;
  return (
    <div
      className="flex flex-col items-center rounded-2xl border border-dashed px-5 pb-5 pt-3"
      style={{
        borderColor: `color-mix(in srgb, ${color} 55%, transparent)`,
        backgroundColor: `color-mix(in srgb, ${color} 4%, transparent)`,
      }}
    >
      {ctx.plain ? (
        <PlainLoopHeader step={step} ctx={ctx} />
      ) : (
        <>
          <div className="mb-3 flex w-full items-center gap-1.5 text-xs" style={{ color }}>
            <LoopIcon className="h-3.5 w-3.5" />
            <span className="font-medium">Repeats for each item</span>
            {step.on_item_failure === "skip" && <span className="text-[var(--muted)]">· skips an item that fails</span>}
            <span className="ml-auto text-[var(--muted)]">at most {step.max_items}</span>
          </div>
          <StepNode step={step} ctx={ctx} />
        </>
      )}
      {step.steps.length > 0 ? (
        <>
          <Arrow />
          {ctx.plain ? <ShortFlow steps={step.steps} ctx={ctx} /> : <Flow steps={step.steps} ctx={ctx} />}
        </>
      ) : (
        <span className="mt-3 text-xs italic text-[var(--muted)]">no steps inside yet</span>
      )}
    </div>
  );
}

function Flow({ steps, ctx }: { steps: WorkflowStep[]; ctx: CanvasContext }) {
  return (
    <div className="flex flex-col items-center">
      {steps.map((step, index) => (
        <Fragment key={step.id}>
          {index > 0 && <Arrow />}
          {(step.kind === "branch" || step.kind === "choice") && <BranchBlock step={step} ctx={ctx} />}
          {step.kind === "loop" && <LoopBlock step={step} ctx={ctx} />}
          {canRecover(step) && step.on_failure?.then === "steps" && <RecoverBlock step={step} ctx={ctx} />}
          {!isBlock(step) && !(canRecover(step) && step.on_failure?.then === "steps") && (
            <StepNode step={step} ctx={ctx} />
          )}
        </Fragment>
      ))}
    </div>
  );
}

/** A read-only picture of a workflow: what runs, in what order, which way
 * a branch can go and what repeats. Clicking a step opens it for editing
 * when `onOpenStep` is given. */
export function WorkflowCanvas({
  workflow,
  run,
  onOpenStep,
  openStepId,
  plain = false,
}: {
  workflow: Workflow;
  /** The step open beside the canvas, whose data stays lit while nothing else is pointed at. */
  openStepId?: string | null;
  /** Draws how this run went on the workflow. */
  run?: ScheduledRun;
  onOpenStep?: (stepId: string) => void;
  /** Plain words instead of tool and variable names, for the task page's simple view. */
  plain?: boolean;
}) {
  const [pointed, setPointed] = useState<string | null>(null);
  const flows = useMemo(() => dataFlow(workflow), [workflow]);
  const focus = pointed ?? openStepId ?? null;
  const ctx = useMemo<CanvasContext>(
    () => ({
      numbers: new Map(placeSteps(everyStep(workflow)).map((placed) => [placed.step.id, placed.number])),
      inputNames: new Set(workflow.inputs.map((input) => input.name)),
      states: run ? runMap(workflow, run) : undefined,
      onOpenStep,
      plain: plain ? { inputs: workflow.inputs } : undefined,
      flow: { flows, focus, setFocus: setPointed },
    }),
    [workflow, run, onOpenStep, plain, flows, focus],
  );
  const fedInputs = focus ? (flows.get(focus)?.inputs ?? new Set<string>()) : new Set<string>();
  const frame = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    // A flow wider than the page opens on its middle, where Start and the main line are.
    const el = frame.current;
    if (el && el.scrollWidth > el.clientWidth) el.scrollLeft = (el.scrollWidth - el.clientWidth) / 2;
  }, [workflow]);
  return (
    <div
      ref={frame}
      data-testid="workflow-canvas"
      className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card-bg)]"
      style={{
        backgroundImage: "radial-gradient(color-mix(in srgb, var(--muted) 30%, transparent) 1px, transparent 1px)",
        backgroundSize: "16px 16px",
      }}
    >
      <div className="mx-auto flex w-max min-w-full flex-col items-center px-8 py-7">
        <Terminal faded={focus !== null && fedInputs.size === 0}>
          <span className="font-medium text-[var(--fg)]">Start</span>
          {workflow.inputs.length > 0 && <span>with</span>}
          {plain ? (
            <span>
              {workflow.inputs.map((input, index) => (
                <Fragment key={input.name}>
                  {index > 0 && ", "}
                  <span className={fedInputs.has(input.name) ? "font-medium text-[var(--kind-script)]" : ""}>
                    {input.label || input.name}
                  </span>
                </Fragment>
              ))}
            </span>
          ) : (
            workflow.inputs.map((input) => <VarToken key={input.name} name={input.name} isInput />)
          )}
        </Terminal>
        <Arrow />
        {workflow.steps.length > 0 ? (
          <Flow steps={workflow.steps} ctx={ctx} />
        ) : (
          <span className="text-xs italic text-[var(--muted)]">No steps yet</span>
        )}
        <Arrow />
        <Terminal faded={run !== undefined && run.status !== "completed"}>
          <span className="font-medium text-[var(--fg)]">Done</span>
        </Terminal>
        {(workflow.after_failure ?? []).length > 0 && <AfterFailure steps={workflow.after_failure ?? []} ctx={ctx} />}
      </div>
    </div>
  );
}
