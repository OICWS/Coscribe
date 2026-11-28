/** The rule that sent a call to the person (conversation/approvals.py's AskReason), in words. */

const SENTENCES: Record<string, string> = {
  command_unsandboxed:
    "Asked because commands on this computer don't run in the elevated sandbox. In Auto mode its reviewer decides them instead.",
  command_online:
    "Asked because commands in this conversation can reach the network, so one could send your files out. In Auto mode its reviewer decides them instead.",
  workspace_rule: "Asked because a rule in this workspace's settings asks for it.",
  auto_review_blocked: "Asked because Auto mode kept blocking actions.",
  auto_review_no_answer: "Asked because Auto mode's reviewer gave no answer.",
  approval_mode: "Asked because the current approval mode asks before this kind of action.",
};

const LABELS: Record<string, string> = {
  command_unsandboxed: "Command without the sandbox",
  command_online: "Command with network",
  workspace_rule: "Workspace rule",
  auto_review_blocked: "Auto mode kept blocking",
  auto_review_no_answer: "Reviewer gave no answer",
  approval_mode: "Approval mode",
};

/** The card's line; null when the reviewer's own note already says why, or the reason is unknown. */
export function askedBecauseText(reason: string | undefined, reviewerNote: string | null | undefined): string | null {
  if (!reason || reviewerNote) return null;
  return SENTENCES[reason] ?? null;
}

export function askedBecauseLabel(reason: string): string {
  return LABELS[reason] ?? reason.replace(/_/g, " ");
}
