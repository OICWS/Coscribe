import { useContext } from "react";
import { BackgroundTasks } from "./contexts";

/** Under a turn the user stopped, the background tasks still going, since a stop does not end
 * them; it opens their panel. Nothing when none run. */
export function StoppedNote({ running }: { running: number }) {
  const background = useContext(BackgroundTasks);
  if (running === 0) return null;
  return (
    <div className="py-1 text-xs text-[var(--muted)]">
      <button type="button" className="hover:text-[var(--fg)] hover:underline" onClick={() => background.open("")}>
        {running} background {running === 1 ? "task" : "tasks"} still running
      </button>
    </div>
  );
}
