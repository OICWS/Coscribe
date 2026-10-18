import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { SlideInfo } from "../../lib/slides";
import { BookOpenIcon, ChevronRightIcon, CloseIcon, ExpandIcon, ShrinkIcon } from "../icons";
import { ChevronLeftIcon } from "./slideIcons";
import { SlideThumb } from "./SlideStrip";

const NEXT_KEYS = ["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"];
const PREVIOUS_KEYS = ["ArrowLeft", "ArrowUp", "PageUp", "Backspace"];

/** CSS animations for PowerPoint's transitions; Magic move has no browser equivalent here, so it
 * fades like PowerPoint does where it finds nothing to move. */
const ENTRANCE: Record<string, string> = {
  fade: "slide-enter-fade",
  morph: "slide-enter-fade",
  push: "slide-enter-push",
};

/** The deck played over the panel, black around the slide; full screen on F. Leaves on Escape
 * or the close button. */
export function SlidePresenter({
  slides,
  start,
  withNotes,
  srcOf,
  onExit,
}: {
  slides: SlideInfo[];
  start: number;
  withNotes: boolean;
  srcOf: (index: number) => string;
  onExit: (last: number) => void;
}) {
  const [index, setIndex] = useState(start);
  const [notesShown, setNotesShown] = useState(withNotes);
  const [fullScreen, setFullScreen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const slide = slides[index];

  useEffect(() => {
    rootRef.current?.focus();
    const onChange = () => setFullScreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const go = (delta: number) => setIndex((i) => Math.max(0, Math.min(slides.length - 1, i + delta)));
  const toggleFullScreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void rootRef.current?.requestFullscreen();
  };
  const exit = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    onExit(index);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // The panel behind has keys of its own; while presenting, only these count.
    e.stopPropagation();
    if (NEXT_KEYS.includes(e.key)) go(1);
    else if (PREVIOUS_KEYS.includes(e.key)) go(-1);
    else if (e.key === "Home") setIndex(0);
    else if (e.key === "End") setIndex(slides.length - 1);
    else if (e.key === "f" || e.key === "F") toggleFullScreen();
    else if (e.key === "Escape" && !document.fullscreenElement) exit();
    else return;
    e.preventDefault();
  };

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      role="dialog"
      aria-label="Presenting"
      className="absolute inset-0 z-30 flex flex-col bg-black outline-none"
      onKeyDown={onKeyDown}
    >
      <div className="relative min-h-0 flex-1" onClick={() => go(1)}>
        {slide && (
          <div key={index} className={`absolute inset-0 ${ENTRANCE[slide.transition ?? ""] ?? ""}`}>
            <SlideThumb src={srcOf(index)} />
          </div>
        )}
      </div>
      {notesShown && slide && (
        <div
          aria-label="Speaker notes"
          className="max-h-[30%] min-h-[72px] shrink-0 overflow-auto whitespace-pre-wrap bg-[#1c1b1a] px-6 py-3 text-[15px] text-white/85"
        >
          {slide.notes || <span className="text-white/45">No speaker notes on this slide.</span>}
        </div>
      )}
      <PresenterBar
        index={index}
        count={slides.length}
        notesShown={notesShown}
        fullScreen={fullScreen}
        onGo={go}
        onToggleNotes={() => setNotesShown((shown) => !shown)}
        onToggleFullScreen={toggleFullScreen}
        onExit={exit}
      />
    </div>
  );
}

const barButton =
  "flex h-8 w-8 items-center justify-center rounded-lg text-white/85 hover:bg-white/10 hover:text-white disabled:opacity-35 disabled:hover:bg-transparent";

/** Previous, the page, next, notes, full screen and stop, under the slide. */
function PresenterBar({
  index,
  count,
  notesShown,
  fullScreen,
  onGo,
  onToggleNotes,
  onToggleFullScreen,
  onExit,
}: {
  index: number;
  count: number;
  notesShown: boolean;
  fullScreen: boolean;
  onGo: (delta: number) => void;
  onToggleNotes: () => void;
  onToggleFullScreen: () => void;
  onExit: () => void;
}) {
  return (
    <div className="flex shrink-0 justify-center py-3">
      <div className="flex items-center gap-0.5 rounded-full bg-[#262524] px-2 py-1 text-white shadow-lg">
        <button
          type="button"
          className={barButton}
          title="Previous slide"
          aria-label="Previous slide"
          disabled={index === 0}
          onClick={() => onGo(-1)}
        >
          <ChevronLeftIcon className="h-4 w-4" />
        </button>
        <span className="px-2 text-sm tabular-nums">
          {index + 1} <span className="text-white/50">/ {count}</span>
        </span>
        <button
          type="button"
          className={barButton}
          title="Next slide"
          aria-label="Next slide"
          disabled={index >= count - 1}
          onClick={() => onGo(1)}
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
        <span className="mx-1 h-4 border-l border-white/20" />
        <button
          type="button"
          className={`${barButton} ${notesShown ? "bg-white/15 text-white" : ""}`}
          title={notesShown ? "Hide speaker notes" : "Show speaker notes"}
          aria-label="Speaker notes"
          aria-pressed={notesShown}
          onClick={onToggleNotes}
        >
          <BookOpenIcon className="h-4 w-4" />
        </button>
        <button
          type="button"
          className={barButton}
          title={fullScreen ? "Leave full screen (F)" : "Full screen (F)"}
          aria-label={fullScreen ? "Leave full screen" : "Full screen"}
          onClick={onToggleFullScreen}
        >
          {fullScreen ? <ShrinkIcon className="h-4 w-4" /> : <ExpandIcon className="h-4 w-4" />}
        </button>
        <button type="button" className={barButton} title="Stop presenting (Esc)" aria-label="Stop presenting" onClick={onExit}>
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
