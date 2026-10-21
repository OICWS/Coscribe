import type { PanelId } from "../../lib/dockLayout";
import { DRAWS_TITLE_BAR, TITLE_BAR_ICON } from "../../lib/titleBar";
import { BrowserIcon, ListChecksIcon, PanelRightIcon, SubAgentsIcon } from "../icons";

const on = "bg-[var(--accent-soft)] text-[var(--accent-ink)]";

/** The panel switches: in the desktop title bar beside Settings, else at
 * the right end of the conversation's header. A panel in a window of its
 * own counts as open; its switch brings that window to the front. */
export function PanelToggles({
  open,
  onToggle,
  hasPlan,
  backgroundTitle,
  running,
  waiting,
}: {
  open: (panel: PanelId) => boolean;
  onToggle: (panel: PanelId) => void;
  /** The Plan switch is shown only while the conversation has a plan or a task list. */
  hasPlan: boolean;
  backgroundTitle: string;
  running: number;
  waiting: number;
}) {
  const task = open("task");
  const background = open("background");
  const icon = DRAWS_TITLE_BAR ? TITLE_BAR_ICON : { className: "h-[18px] w-[18px]" };
  const off = DRAWS_TITLE_BAR
    ? "text-[var(--fg)] hover:bg-[var(--card-bg)]"
    : "text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
  return (
    <>
      <button
        type="button"
        title={task ? "Hide task details" : "Show task details"}
        aria-pressed={task}
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${task ? on : off}`}
        onClick={() => onToggle("task")}
      >
        <PanelRightIcon {...icon} />
      </button>
      {hasPlan && (
        <button
          type="button"
          title="Plan"
          aria-pressed={open("plan")}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${open("plan") ? on : off}`}
          onClick={() => onToggle("plan")}
        >
          <ListChecksIcon {...icon} />
        </button>
      )}
      <button
        type="button"
        title="Browser"
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${open("browser") ? on : off}`}
        onClick={() => onToggle("browser")}
      >
        <BrowserIcon {...icon} />
      </button>
      <button
        type="button"
        title={backgroundTitle}
        className={`relative flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${background ? on : off}`}
        onClick={() => onToggle("background")}
      >
        <SubAgentsIcon {...icon} />
        {running > 0 && (
          <span
            aria-label={waiting > 0 ? `${running} running, ${waiting} waiting for you` : `${running} running`}
            className={`absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-medium leading-none ${
              waiting > 0 ? "bg-[var(--warning)] text-[var(--bg)]" : "bg-[var(--accent)] text-[var(--accent-fg)] motion-safe:animate-pulse"
            }`}
          >
            {running}
          </span>
        )}
      </button>
    </>
  );
}
