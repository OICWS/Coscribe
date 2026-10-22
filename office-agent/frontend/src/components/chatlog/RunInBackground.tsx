import { useContext, useState } from "react";
import { isRunning } from "../../lib/transcriptGrouping";
import { DetachScript } from "./contexts";
import { type ToolOrApprovalItem } from "./types";

const SCRIPT_TOOLS = new Set(["run_python_script", "run_node_script"]);

/** Lets a script that is still running carry on as a background task, so the conversation
 * can go on. Only the two script tools have it, and only in the main conversation. */
export function RunInBackground({ item, live }: { item: ToolOrApprovalItem; live: boolean }) {
  const detach = useContext(DetachScript);
  const [sent, setSent] = useState(false);
  const script = item.arguments.script;
  if (!detach || !SCRIPT_TOOLS.has(item.toolName) || typeof script !== "string" || !isRunning(item, live)) return null;
  return (
    <button
      type="button"
      disabled={sent}
      className="mt-1 rounded-md border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-60"
      onClick={() => {
        setSent(true);
        detach(script);
      }}
    >
      {sent ? "Moving to background…" : "Run in background"}
    </button>
  );
}
