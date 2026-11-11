import { useState, type ReactNode } from "react";
import { CloseIcon } from "./icons";

export interface NoticeAction {
  label: string;
  onClick: () => void;
  title?: string;
  disabled?: boolean;
}

/** One thing waiting on the person, kept above the message box until they act on it or close it. */
export interface Notice {
  id: string;
  icon: ReactNode;
  title: string;
  /** A few words after the title. */
  detail?: string;
  /** Where it stands, at the right: "Tested", "Testing 2/5". */
  state?: string;
  /** Ready to act on (a draft whose test passed): the row turns lavender. */
  ready?: boolean;
  /** Clicking the row's text, e.g. to scroll to what the notice is about. */
  onOpen?: () => void;
  actions: NoticeAction[];
  onDismiss?: () => void;
  dismissTitle?: string;
}

function NoticeRow({ notice }: { notice: Notice }) {
  const fg = notice.ready ? "text-[var(--notice-ready-fg)]" : "text-[var(--notice-fg)]";
  const text = (
    <>
      <span className="min-w-0 truncate" title={notice.title}>
        {notice.title}
      </span>
      {notice.detail && (
        <span className="min-w-0 shrink-[3] truncate max-sm:hidden" title={notice.detail}>
          {notice.detail}
        </span>
      )}
    </>
  );
  return (
    <div
      className={`flex min-h-[52px] min-w-0 items-center gap-3 rounded-xl px-4 font-mono text-[14px] ${fg} ${
        notice.ready ? "bg-[var(--notice-ready-bg)]" : "bg-[var(--notice-bg)]"
      }`}
      data-testid="notice"
    >
      <span className={`flex h-4 w-4 shrink-0 items-center justify-center ${notice.ready ? "" : "text-[var(--notice-icon)]"}`}>
        {notice.icon}
      </span>
      {notice.onOpen ? (
        <button type="button" className="flex min-w-0 flex-1 items-center gap-3 text-left" onClick={notice.onOpen}>
          {text}
        </button>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3">{text}</div>
      )}
      {notice.state && <span className="shrink-0 whitespace-nowrap font-sans text-[14px]">{notice.state}</span>}
      {notice.actions.map((action) => (
        <button
          key={action.label}
          type="button"
          className="h-8 shrink-0 whitespace-nowrap rounded-lg bg-[var(--notice-pill-bg)] px-2.5 font-sans text-[14px] text-[var(--notice-pill-fg)] hover:brightness-95 disabled:opacity-50"
          title={action.title}
          disabled={action.disabled}
          onClick={action.onClick}
        >
          {action.label}
        </button>
      ))}
      {notice.onDismiss && (
        <button
          type="button"
          aria-label="Close"
          title={notice.dismissTitle ?? "Close"}
          className="-mr-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-[color-mix(in_srgb,currentColor_10%,transparent)]"
          onClick={notice.onDismiss}
        >
          <CloseIcon className="h-[18px] w-[18px]" />
        </button>
      )}
    </div>
  );
}

const COLLAPSED = 2;

/** The notices waiting on the person, newest first: two show, and the rest open on "Show N more". */
export function NoticeStack({ notices }: { notices: Notice[] }) {
  const [open, setOpen] = useState(false);
  if (notices.length === 0) return null;
  const newestFirst = [...notices].reverse();
  const shown = open ? newestFirst : newestFirst.slice(0, COLLAPSED);
  const more = notices.length - COLLAPSED;
  return (
    <div className="mx-auto w-full max-w-[880px] px-4 pb-2">
      <div role="region" aria-label="Notices" className="flex flex-col gap-1.5" data-testid="notice-stack">
        <div className={`flex flex-col gap-1.5 ${open ? "max-h-[40vh] overflow-y-auto" : ""}`}>
          {shown.map((notice) => (
            <NoticeRow key={notice.id} notice={notice} />
          ))}
        </div>
        {more > 0 && (
          <button
            type="button"
            className="self-start px-2 text-[14px] text-[var(--fg)] hover:underline"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? "Show less" : `Show ${more} more`}
          </button>
        )}
      </div>
    </div>
  );
}
