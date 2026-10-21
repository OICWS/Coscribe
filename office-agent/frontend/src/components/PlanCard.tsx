import { useState } from "react";
import type { LogItem } from "../state/reducer";
import { Disclosure } from "./chatlog/SummaryLabel";
import { MoreIcon } from "./icons";

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

  const buttons = "h-8 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-2.5 text-[14px] hover:bg-[var(--card-bg)]";
  const primary = "h-8 rounded-lg bg-[var(--primary)] px-3 text-[14px] font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)]";

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-[15px] font-medium">Claude proposed a plan</p>
          {onOpenPlan && (
            <button type="button" className="text-[14px] text-[var(--accent)] underline underline-offset-2" onClick={onOpenPlan}>
              Open plan
            </button>
          )}
        </div>
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
              <button type="button" className={primary} onClick={() => onAnswer(item, "auto", "")}>
                Accept and auto mode
              </button>
            </div>
          </div>
        )}
        {pending && onAnswer && revising && (
          <form
            className="mt-3 flex flex-col gap-3"
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
              className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-[15px] outline-none focus:border-[var(--accent)]"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
            />
            <div className="flex items-center justify-between">
              <button type="button" className={buttons} onClick={() => setRevising(false)}>
                Back
              </button>
              <button type="submit" className={primary}>
                Revise
              </button>
            </div>
          </form>
        )}
      </div>
      <div>
        <button
          type="button"
          aria-expanded={source}
          className="flex items-center gap-3 text-[15px] text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => setSource(!source)}
        >
          <MoreIcon className="h-4 w-4 shrink-0 rotate-90" />
          <span className="flex items-center gap-1">
            Proposing plan
            <Disclosure open={source} />
          </span>
        </button>
        {source && (
          <pre className="ml-7 mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3 font-sans text-[15px] leading-relaxed">
            {item.plan}
          </pre>
        )}
      </div>
    </div>
  );
}
