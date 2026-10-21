import type { ReactNode } from "react";
import { COLLAPSED_CLUSTER_WIDTH, TITLE_BAR_ICON } from "../lib/titleBar";
import { HelpIcon, MoreIcon, SettingsIcon } from "./icons";
import { NAV_RAIL_EXPANDED_WIDTH } from "./NavRail";

interface HeaderProps {
  /** The sidebar takes layout space of its own, so the header starts after it. */
  navPinned: boolean;
  title: ReactNode;
  /** The panel toggles of a conversation; nothing on the other pages. */
  toggles: ReactNode;
  onSettings: () => void;
}

/** The desktop window's title bar: the sidebar's top row covers its left end, the OS window
 * buttons its right end. */
export function TitleBar({ navPinned, title, toggles, onSettings }: HeaderProps) {
  return (
    <div className="flex h-10 shrink-0 items-center">
      <div className="shrink-0" style={{ width: navPinned ? NAV_RAIL_EXPANDED_WIDTH : COLLAPSED_CLUSTER_WIDTH }} />
      <div className="titlebar-drag flex h-full min-w-0 flex-1 items-center pl-2 pr-4">{title}</div>
      {toggles && <div className="mr-1 flex shrink-0 items-center gap-1">{toggles}</div>}
      <button
        type="button"
        title="Settings"
        aria-label="Settings"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--fg)] hover:bg-[var(--card-bg)]"
        onClick={onSettings}
      >
        <MoreIcon {...TITLE_BAR_ICON} />
      </button>
      {/* Keeps Settings apart from the OS minimize button, so the two
       * aren't mistaken for one group. */}
      <div className="w-3 shrink-0" />
      <div className="titlebar-controls-space" />
    </div>
  );
}

/** Outside the desktop shell, which has a title bar for all of this. pl-12 clears NavRail's
 * collapsed 48px toggle, absolutely placed over this row's left end; rows below don't need it. */
export function PageHeader({ navPinned, title, toggles, onSettings, onShortcuts }: HeaderProps & { onShortcuts: () => void }) {
  const button = "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
  return (
    <div className={`flex h-12 shrink-0 items-center gap-1 pr-4 ${navPinned ? "pl-4" : "pl-12"}`}>
      {title}
      {toggles}
      <button type="button" title="Keyboard shortcuts (?)" className={button} onClick={onShortcuts}>
        <HelpIcon className="h-[18px] w-[18px]" />
      </button>
      <button type="button" title="Settings" className={button} onClick={onSettings}>
        <SettingsIcon className="h-[18px] w-[18px]" />
      </button>
    </div>
  );
}
