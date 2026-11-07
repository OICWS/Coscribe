import { useContext } from "react";
import { StopIcon } from "../icons";
import { BackgroundTasks } from "./contexts";

/** The quiet line under a turn the user stopped; a stop leaves background tasks going, so it says
 * how many and opens their panel. */
export function StoppedNote({ running }: { running: number }) {
  const background = useContext(BackgroundTasks);
  return (
    <div className="flex items-center gap-1.5 py-1 text-xs text-[var(--muted)]">
      <StopIcon className="h-3 w-3 shrink-0" />
      <span>Stopped · What should I do instead?</span>
      {running > 0 && (
        <>
          <span aria-hidden>·</span>
          <button type="button" className="hover:text-[var(--fg)] hover:underline" onClick={() => background.open("")}>
            {running} background {running === 1 ? "task" : "tasks"} still running
          </button>
        </>
      )}
    </div>
  );
}
