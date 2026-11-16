import { useState, type ReactNode } from "react";
import { CloseIcon } from "./icons";

interface NoticeAction {
  label: string;
  /** Shown instead of the label, which then names the button for screen readers and on hover. */
  icon?: ReactNode;
  onClick: () => void;
  title?: string;
  disabled?: boolean;
}

/** One thing waiting on the person, kept above the message box until they act on it or close it. */
export interface Notice {
  id: string;
  icon: ReactNode;
  /** Pictures shown in place of the icon, overlapping when there are several. */
  thumbnails?: string[];
  title: string;
  /** A name the person gave or will read as one (a document's title): the body font, in the text
   * colour. Otherwise the title is set in mono, like a branch or a file name. */
  plainTitle?: boolean;
  /** A few words after the title. */
  detail?: string;
  /** The detail in the body font, as words rather than code. */
  plainDetail?: boolean;
  /** Where it stands, at the right: "Tested", "Testing 2/5". */
  state?: string;
  /** Ready to act on (a draft whose test passed): the row turns lavender. */
  ready?: boolean;
  /** Clicking the row's text, e.g. to scroll to what the notice is about. */
  onOpen?: () => void;
  openTitle?: string;
  actions: NoticeAction[];
  onDismiss?: () => void;
  dismissTitle?: string;
}

function Thumbnails({ sources }: { sources: string[] }) {
  return (
    <span className="flex shrink-0" aria-hidden="true">
      {sources.slice(0, 3).map((src, i) => (
        <img
          key={src}
          src={src}
          alt=""
          loading="lazy"
          className={`h-6 w-9 rounded-[5px] border border-[var(--border)] bg-[var(--bg)] object-cover ${
            i > 0 ? "-ml-3.5 shadow-[0_0_0_2px_var(--notice-bg)]" : ""
          }`}
        />
      ))}
    </span>
  );
}

function NoticeRow({ notice }: { notice: Notice }) {
  const fg = notice.ready ? "text-[var(--notice-ready-fg)]" : "text-[var(--notice-fg)]";
  const text = (
    <>
      <span className={`min-w-0 truncate ${notice.plainTitle ? "font-sans text-[var(--fg)]" : ""}`} title={notice.title}>
        {notice.title}
      </span>
      {notice.detail && (
        <span className={`min-w-0 shrink-[3] truncate max-sm:hidden ${notice.plainTitle || notice.plainDetail ? "font-sans" : ""}`} title={notice.detail}>
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
      {notice.thumbnails?.length ? (
        <Thumbnails sources={notice.thumbnails} />
      ) : (
        <span className={`flex h-4 w-4 shrink-0 items-center justify-center ${notice.ready ? "" : "text-[var(--notice-icon)]"}`}>
          {notice.icon}
        </span>
      )}
      {notice.onOpen ? (
        <button type="button" className="flex min-w-0 flex-1 items-center gap-3 text-left" title={notice.openTitle} onClick={notice.onOpen}>
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
          className={`flex h-8 shrink-0 items-center justify-center whitespace-nowrap rounded-lg bg-[var(--notice-pill-bg)] font-sans text-[14px] text-[var(--notice-pill-fg)] hover:brightness-95 disabled:opacity-50 ${
            action.icon ? "w-8" : "px-2.5"
          }`}
          title={action.title ?? (action.icon ? action.label : undefined)}
          aria-label={action.icon ? action.label : undefined}
          disabled={action.disabled}
          onClick={action.onClick}
        >
          {action.icon ?? action.label}
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
