import { useEffect, useState } from "react";
import { planTitleOf, type PlanChoice, type PlanItem } from "../lib/planState";
import { usePlanTaskDraft, draftEdits } from "../lib/planTaskDraft";
import { Disclosure } from "./chatlog/index";
import { PlanDiff } from "./PlanDiff";

export type { PlanChoice, PlanItem };

const OUTCOME: Record<Exclude<PlanItem["status"], "pending">, string> = {
  auto: "Accepted. Carrying it out in auto mode",
  manual: "Accepted",
  revise: "Sent back with your feedback",
  reject: "Rejected. Nothing will be done",
};

/** Ctrl/Cmd+Enter typed into a field is the field's own (a new line in the message box). */
function inField(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

/** The plan the model proposed, in plan mode or before a large task. Accepting
 * it carries it out, in auto mode (the main choice, Ctrl+Enter) or with the
 * approvals as they were; Revise sends it back with what to change; Reject
 * ends the planning. The plan itself is a document in the Plan panel, where
 * its task list can be edited until it is answered. */
const buttons = "h-8 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-2.5 text-[14px] hover:bg-[var(--card-bg)]";
const primary = "h-8 rounded-lg bg-[var(--primary)] px-3 text-[14px] font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]";

function ReviseForm({ onBack, onRevise }: { onBack: () => void; onRevise: (feedback: string) => void }) {
  const [feedback, setFeedback] = useState("");
  return (
    <form
      className="mt-3 flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        onRevise(feedback);
      }}
    >
      <textarea
        aria-label="What should change?"
        placeholder="What should change? (optional)"
        rows={3}
        autoFocus
        className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-[15px] outline-none focus:border-[var(--accent)]"
        value={feedback}
        onChange={(event) => setFeedback(event.target.value)}
      />
      <div className="flex items-center justify-between">
        <button type="button" className={buttons} onClick={onBack}>
          Back
        </button>
        <button type="submit" className={primary}>
          Revise
        </button>
      </div>
    </form>
  );
}

export function PlanCard({
  item,
  onAnswer,
  onOpenPlan,
}: {
  item: PlanItem;
  onAnswer?: (item: PlanItem, choice: PlanChoice, feedback: string) => void;
  onOpenPlan?: () => void;
}) {
  const [revising, setRevising] = useState(false);
  const [source, setSource] = useState(false);
  const pending = item.status === "pending";
  const draft = usePlanTaskDraft(pending ? item.id : null);
  const edited = draft !== null && draftEdits(item.id) !== undefined;
  const title = planTitleOf(item.plan);

  useEffect(() => {
    if (!pending || !onAnswer) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey) || event.isComposing || inField(event.target)) return;
      event.preventDefault();
      onAnswer(item, "auto", "");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending, onAnswer, item]);

  return (
    <div className="flex flex-col gap-3" data-waiting={pending ? item.id : undefined}>
      {item.previous !== undefined && <PlanDiff before={item.previous} after={item.plan} />}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-[15px] font-medium">Claude proposed a plan</p>
          {onOpenPlan && (
            <button type="button" className="cursor-pointer text-[14px] text-[var(--accent)] underline-offset-2 transition-colors hover:text-[color-mix(in_srgb,var(--accent)_85%,var(--bg))] hover:underline focus-visible:underline" onClick={onOpenPlan}>
              Open plan
            </button>
          )}
        </div>
        {title && <p className="mt-0.5 truncate text-[14px] text-[var(--muted)]">{title}</p>}
        {pending && edited && <p className="mt-1 text-[13px] text-[var(--accent)]">You changed the task list; Accept carries out your version.</p>}
        {item.status !== "pending" && <p className="mt-1 text-[13px] text-[var(--muted)]">{OUTCOME[item.status]}</p>}
        {pending && onAnswer && !revising && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <button type="button" className={buttons} onClick={() => onAnswer(item, "reject", "")}>
                Reject
              </button>
              <button type="button" className={buttons} onClick={() => setRevising(true)}>
                Revise…
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className={buttons} onClick={() => onAnswer(item, "manual", "")}>
                Accept
              </button>
              <button
                type="button"
                aria-label="Accept and use auto mode"
                aria-keyshortcuts="Control+Enter"
                className={`${primary} inline-flex items-center gap-2`}
                onClick={() => onAnswer(item, "auto", "")}
              >
                Accept and use auto mode
                <kbd className="rounded border border-current/30 px-1 font-sans text-[12px] opacity-80">Ctrl ⏎</kbd>
              </button>
            </div>
          </div>
        )}
        {pending && onAnswer && revising && (
          <ReviseForm onBack={() => setRevising(false)} onRevise={(feedback) => onAnswer(item, "revise", feedback)} />
        )}
      </div>
      <div className="w-full text-sm">
        <button
          type="button"
          aria-expanded={source}
          className="inline-flex max-w-full items-center gap-1 text-left text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => setSource(!source)}
        >
          Proposing plan
          <Disclosure open={source} />
        </button>
        {source && (
          <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3 font-sans text-[15px] leading-relaxed">
            {item.plan}
          </pre>
        )}
      </div>
    </div>
  );
}
