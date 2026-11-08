import { SkillIcon, WorkflowIcon } from "./icons";

interface SaveOfferRowProps {
  offer: { steps: number; name: string };
  /** Each gets the job's name; the row goes away once one is picked. */
  onWorkflow: (name: string) => void;
  onSkill: (name: string) => void;
  onDismiss: () => void;
}

const buttonClass =
  "inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 py-1 text-[13px] font-medium hover:border-[var(--border-hover)] hover:bg-[var(--card-bg)]";

/** After a turn that did a job someone would do again: save it, so it can run again or on a schedule. */
export function SaveOfferRow({ offer, onWorkflow, onSkill, onDismiss }: SaveOfferRowProps) {
  const pick = (save: (name: string) => void) => () => {
    onDismiss();
    save(offer.name);
  };
  return (
    <div className="mx-auto w-full max-w-[880px] px-4 pb-2">
      <div role="region" aria-label="Save this job" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-[var(--border)] py-2 pl-4 pr-2 text-sm">
        <span className="min-w-0 flex-1 text-[var(--muted)]">That took {offer.steps} steps. Save it so you can run it again, or on a schedule?</span>
        <div className="flex shrink-0 items-center gap-1.5">
          <button type="button" className={buttonClass} onClick={pick(onWorkflow)} title="Fixed steps you can rerun or schedule">
            <WorkflowIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
            Save as workflow
          </button>
          <button type="button" className={buttonClass} onClick={pick(onSkill)} title="Instructions the assistant follows next time">
            <SkillIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
            Save as skill
          </button>
          <button type="button" className="rounded-lg px-2 py-1 text-[13px] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]" onClick={onDismiss}>
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
