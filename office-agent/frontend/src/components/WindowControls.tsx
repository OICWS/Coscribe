import { useEffect, useState, type MouseEvent } from "react";
import { showAppMenu } from "../lib/electron";
import { TITLE_BAR_ICON } from "../lib/titleBar";
import { ArrowLeftIcon, ArrowRightIcon, MenuIcon } from "./icons";

const iconButton =
  "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--fg)] hover:bg-[var(--card-bg)] disabled:opacity-35 disabled:hover:bg-transparent";

interface NavigationLike extends EventTarget {
  canGoBack: boolean;
  canGoForward: boolean;
}

/** Chromium's Navigation API, which knows whether Back/Forward lead
 * anywhere; the History API doesn't. */
function navigationApi(): NavigationLike | null {
  return (window as unknown as { navigation?: NavigationLike }).navigation ?? null;
}

function readAvailability(): { back: boolean; forward: boolean } {
  const nav = navigationApi();
  return { back: nav?.canGoBack ?? true, forward: nav?.canGoForward ?? true };
}

function useHistoryAvailability(): { back: boolean; forward: boolean } {
  const [state, setState] = useState(readAvailability);
  useEffect(() => {
    const nav = navigationApi();
    if (!nav) return;
    const update = () => setState(readAvailability());
    nav.addEventListener("currententrychange", update);
    return () => nav.removeEventListener("currententrychange", update);
  }, []);
  return state;
}

/** The application menu (File/Edit/View/Go/Window/Help); the OS menu bar is hidden. */
export function AppMenuButton() {
  const open = (event: MouseEvent<HTMLButtonElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    showAppMenu(rect.left, rect.bottom + 4);
  };
  return (
    <button type="button" title="Menu" aria-label="Menu" className={iconButton} onClick={open}>
      <MenuIcon {...TITLE_BAR_ICON} />
    </button>
  );
}

/** Back and Forward through the pages visited in this window. */
export function HistoryButtons() {
  const { back, forward } = useHistoryAvailability();
  return (
    <>
      <button
        type="button"
        title="Back"
        aria-label="Back"
        disabled={!back}
        className={iconButton}
        onClick={() => window.history.back()}
      >
        <ArrowLeftIcon {...TITLE_BAR_ICON} />
      </button>
      <button
        type="button"
        title="Forward"
        aria-label="Forward"
        disabled={!forward}
        className={iconButton}
        onClick={() => window.history.forward()}
      >
        <ArrowRightIcon {...TITLE_BAR_ICON} />
      </button>
    </>
  );
}
