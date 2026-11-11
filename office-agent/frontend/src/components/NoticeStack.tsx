import { useState, type ReactNode } from "react";
import { primaryButton, secondaryButton } from "../lib/formStyles";
import { CloseIcon } from "./icons";

export interface NoticeAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
  title?: string;
  disabled?: boolean;
}

/** One thing waiting on the person, kept above the message box until they act on it or close it. */
export interface Notice {
  id: string;
  icon: ReactNode;
  title: string;
  /** One line under the title. */
  detail?: ReactNode;
  /** Clicking the title, e.g. to scroll to what the notice is about. */
  onOpen?: () => void;
  actions: NoticeAction[];
  onDismiss?: () => void;
  dismissTitle?: string;
}

const primaryClass = `${primaryButton} shrink-0 whitespace-nowrap`;
const secondaryClass = `${secondaryButton} shrink-0 whitespace-nowrap`;

function NoticeRow({ notice }: { notice: Notice }) {
  const heading = (
    <>
      <div className="truncate text-[13px] font-medium" title={notice.title}>
        {notice.title}
      </div>
      {notice.detail && <div className="min-w-0 truncate text-[13px] text-[var(--muted)]">{notice.detail}</div>}
    </>
  );
  return (
    <div
      className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] px-3 py-1.5"
      data-testid="notice"
    >
      <span className="flex h-4 w-4 shrink-0 items-center justify-center text-[var(--muted)]">{notice.icon}</span>
      {notice.onOpen ? (
        <button type="button" className="min-w-[10rem] flex-1 text-left" onClick={notice.onOpen}>
          {heading}
        </button>
      ) : (
        <div className="min-w-[10rem] flex-1">{heading}</div>
      )}
      <div className="ml-auto flex shrink-0 items-center gap-1.5">
        {notice.actions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={action.primary ? primaryClass : secondaryClass}
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
            className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={notice.onDismiss}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        )}
      </div>
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
            className="self-start px-1 text-[12px] text-[var(--muted)] hover:text-[var(--fg)]"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? "Show less" : `Show ${more} more`}
          </button>
        )}
      </div>
    </div>
  );
}
