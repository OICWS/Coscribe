import { DRAWS_TITLE_BAR, TITLE_BAR_ICON } from "../../lib/titleBar";
import { BrowserIcon, PanelRightIcon, SubAgentsIcon } from "../icons";

const on = "bg-[var(--accent-soft)] text-[var(--accent-ink)]";

/** The panel switches: in the desktop title bar beside Settings, else at
 * the right end of the conversation's header. A panel in a window of its
 * own counts as open; its switch brings that window to the front. */
export function PanelToggles({
  task,
  browser,
  background,
  onTask,
  onBrowser,
  onBackground,
  backgroundTitle,
  running,
  waiting,
}: {
  task: boolean;
  browser: boolean;
  background: boolean;
  onTask: () => void;
  onBrowser: () => void;
  onBackground: () => void;
  backgroundTitle: string;
  running: number;
  waiting: number;
}) {
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
        onClick={onTask}
      >
        <PanelRightIcon {...icon} />
      </button>
      <button
        type="button"
        title="Browser"
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${browser ? on : off}`}
        onClick={onBrowser}
      >
        <BrowserIcon {...icon} />
      </button>
      <button
        type="button"
        title={backgroundTitle}
        className={`relative flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${background ? on : off}`}
        onClick={onBackground}
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
