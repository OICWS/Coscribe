import type { ReactNode } from "react";
import { askedBecauseLabel } from "../lib/askedBecause";
import type { ApprovalSummary, ThreadActivity } from "../types/session";

export function Chip({ label, count }: { label: string; count?: number }) {
  return (
    <span className="inline-flex max-w-full items-center gap-1 rounded-full border border-[var(--border)] px-2 py-0.5 text-xs">
      <span className="truncate">{label}</span>
      {count !== undefined && count > 1 && <span className="tabular-nums text-[var(--muted)]">×{count}</span>}
    </span>
  );
}

export function ContextGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">{label}</div>
      {children}
    </div>
  );
}

export function hasApprovals(activity: ThreadActivity): boolean {
  const approvals = activity.approvals;
  return approvals !== undefined && approvals.asked + approvals.approved_without_asking > 0;
}

/** How often the conversation's gated calls asked the person, and which rules made them ask. */
export function ApprovalCounts({ approvals }: { approvals: ApprovalSummary }) {
  return (
    <ContextGroup label="Approvals">
      <p className="mb-1.5 text-[13px] text-[var(--muted)]">
        {approvals.asked} asked you · {approvals.approved_without_asking} went ahead without asking
      </p>
      {approvals.asked_because.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {[...approvals.asked_because]
            .sort((a, b) => b.count - a.count)
            .map((entry) => (
              <Chip key={entry.reason} label={askedBecauseLabel(entry.reason)} count={entry.count} />
            ))}
        </div>
      )}
    </ContextGroup>
  );
}
