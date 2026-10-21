import { useState } from "react";
import type { LogItem } from "../state/reducer";
import { primaryButton, secondaryButton } from "../lib/formStyles";
import { Disclosure } from "./chatlog/SummaryLabel";

export type PlanItem = Extract<LogItem, { kind: "plan" }>;
export type PlanChoice = "auto" | "manual" | "revise" | "reject";

const OUTCOME: Record<Exclude<PlanItem["status"], "pending">, string> = {
  auto: "Accepted. Carrying it out in auto mode",
  manual: "Accepted. You'll approve each change",
  revise: "Sent back with your feedback",
  reject: "Rejected. Nothing will be done",
};

/** The plan the model proposed in plan mode. Accepting it leaves plan mode,
 * in auto mode or approving each change by hand; Revise sends it back with
 * what to change; Reject ends the planning. The plan itself is a document
 * in the Plan panel, its source one row above. */
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
  const [feedback, setFeedback] = useState("");
  const [source, setSource] = useState(false);
  const pending = item.status === "pending";

  return (
    <div className="flex flex-col gap-2">
      <div>
        <button
          type="button"
          aria-expanded={source}
          className="flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => setSource(!source)}
        >
          Proposing plan
          <Disclosure open={source} />
        </button>
        {source && (
          <pre className="mt-1.5 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 font-mono text-xs leading-relaxed">
            {item.plan}
          </pre>
        )}
      </div>
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-4">
        <p className="text-[15px] font-medium">Claude proposed a plan</p>
        {item.status !== "pending" && <p className="mt-1 text-[13px] text-[var(--muted)]">{OUTCOME[item.status]}</p>}
        {pending && onAnswer && !revising && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button type="button" className={secondaryButton} onClick={() => onAnswer(item, "reject", "")}>
              Reject
            </button>
            <button type="button" className={secondaryButton} onClick={() => setRevising(true)}>
              Revise…
            </button>
            <button type="button" className={secondaryButton} onClick={() => onAnswer(item, "manual", "")}>
              Accept
            </button>
            <button type="button" className={primaryButton} onClick={() => onAnswer(item, "auto", "")}>
              Accept and auto mode
            </button>
          </div>
        )}
        {pending && onAnswer && revising && (
          <form
            className="mt-3 flex flex-col gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              onAnswer(item, "revise", feedback);
            }}
          >
            <textarea
              aria-label="What should change?"
              placeholder="What should change? (optional)"
              rows={3}
              autoFocus
              className="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm outline-none focus:border-[var(--border-hover)]"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
            />
            <div className="flex gap-2">
              <button type="button" className={secondaryButton} onClick={() => setRevising(false)}>
                Back
              </button>
              <button type="submit" className={primaryButton}>
                Revise
              </button>
            </div>
          </form>
        )}
        {onOpenPlan && (
          <button type="button" className="mt-3 text-[13px] text-[var(--muted)] underline-offset-2 hover:text-[var(--fg)] hover:underline" onClick={onOpenPlan}>
            Open plan
          </button>
        )}
      </div>
    </div>
  );
}
