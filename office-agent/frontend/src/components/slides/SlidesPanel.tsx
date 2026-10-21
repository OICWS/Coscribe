import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { openThreadFile } from "../../lib/rest";
import {
  DeckNotBuilt,
  fitZoom,
  getSlideDeck,
  saveBlob,
  slideExport,
  slideImageUrl,
  stepZoom,
  type SlideDeck,
  type SlideExport,
  type SlideInfo,
} from "../../lib/slides";
import { useDockPanel } from "../dock/dockContext";
import { ChevronDownIcon, ExternalLinkIcon, MessageCircleIcon } from "../icons";
import type { CommentLink } from "../../lib/slideComments";
import { SlideComments, useSlideComments, type CommentStart } from "./SlideComments";
import { SlideEditor } from "./SlideEditor";
import { SlideInsertBar } from "./SlideInsertBar";
import { ConfirmDialog } from "../ConfirmDialog";
import { NewSlideDialog } from "./NewSlideDialog";
import { useSlideArranging } from "./useSlideArranging";
import { useSlideHistory } from "./useSlideHistory";
import { downloadEntries, presentEntries, titleEntries, zoomEntries } from "./slideMenus";
import { setNotes, type Insert } from "../../lib/slideSource";
import { editSlide, getSlideParts } from "../../lib/slideEditing";
import { SlideMenu, type MenuEntry } from "./SlideMenu";
import { SlidePresenter } from "./SlidePresenter";
import { SlideProperties } from "./SlideProperties";
import type { EditorSelection } from "./SlideTextProperties";
import { useDesignSystem } from "./useDesignSystem";
import { CANVAS_GAP, MARGIN, SlideStage, TOOLBAR_ROOM } from "./SlideStage";
import { SlideToolbar } from "./SlideToolbar";
import { SlideFooter, SlideMiniBar, SlideThumbnails, type SlidesView } from "./SlideStrip";

/** From this panel width the properties sit beside the slide instead of below it. */
const PROPERTIES_BESIDE_FROM = 880;

type Menu = { kind: "zoom" | "title" | "present" | "download" | "comments"; anchor: DOMRect };

/** A deck coscribe built, beside the conversation: the slide, its thumbnails, its notes and
 * properties, and all slides at once in Canvas view. A click on the slide starts editing it. */
export function SlidesPanel({
  threadId,
  path,
  refreshKey,
  onSendComment,
}: {
  threadId: string;
  path: string;
  refreshKey: string;
  /** Sends a comment to coscribe as a message; absent where there is no conversation. */
  onSendComment?: (text: string, link: CommentLink) => void;
}) {
  const edits = useEdits(threadId, path);
  const { deck, error, notBuilt, open, srcOf } = useSlideDeck(threadId, path, `${refreshKey}.${edits.count}`);
  const comments = useSlideComments(threadId, path, refreshKey);
  const design = useDesignSystem(threadId, path);
  const [menu, setMenu] = useState<Menu | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const { stage, panelWidth } = useSizes(rootRef, stageRef, deck !== null);
  const downloads = useSlideDownloads(threadId, path, srcOf);

  const slides = deck?.slides ?? [];
  const ui = useSlidesUi(slides.length);
  const { index, view, setCurrent } = ui;
  const history = useSlideHistory(threadId, path, `${refreshKey}.${edits.count}`, () => edits.changed(() => undefined), edits.setProblem);
  const arranging = useSlideArranging({ threadId, path, loadSource: edits.loadSource, onDone: (at) => edits.changed(() => setCurrent(at)), onProblem: edits.setProblem });
  const shownZoom = ui.zoom ?? fitFor(view, stage);
  const name = path.split(/[\\/]/).pop() ?? path;
  const slide = slides[index];
  const beside = panelWidth >= PROPERTIES_BESIDE_FROM;
  const properties = ui.propertiesShown && slide && (
    <SlideProperties slide={slide} beside={beside} selection={ui.selection} design={design} onEdit={(change) => edits.edit(index, change)} loadSource={() => edits.loadSource(index)} onClose={() => ui.setPropertiesShown(false)} />
  );

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      className="relative flex h-full min-h-0 flex-col outline-none"
      onKeyDown={(e) => ui.onKey(e, shownZoom, history.step)}
    >
      <PanelTop title={deck?.title ?? name} path={path} ui={ui} onMenu={(kind, anchor) => setMenu({ kind, anchor })} />
      <DeckNotices changed={deck?.changed ?? false} error={error ?? edits.problem ?? downloads.failed ?? comments.failed} />
      {notBuilt ? (
        <NotBuilt name={name} onOpen={() => open(false)} />
      ) : (
        <div className="flex min-h-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            <SlideStage
              ref={stageRef}
              view={view}
              slides={slides}
              current={index}
              zoom={shownZoom}
              srcOf={srcOf}
              onSelect={setCurrent}
              onWheelZoom={(direction) => ui.setZoom(stepZoom(shownZoom, direction))}
              onOpen={ui.openSlide}
              overlay={
                slide && (
                  <SlideLayers at={{ threadId, path, ui, zoom: shownZoom }} edits={edits} refreshKey={refreshKey}>
                    <SlideComments
                      threadId={threadId}
                      path={path}
                      deckName={name}
                      slide={slide}
                      slideNumber={index + 1}
                      store={comments}
                      commenting={ui.commenting}
                      showResolved={ui.showResolved}
                      onSend={onSendComment}
                      startAt={ui.commentAt}
                    />
                  </SlideLayers>
                )
              }
            >
              <StageControls ui={ui} count={slides.length} zoom={shownZoom} beside={beside} busy={downloads.busy} 
                onMenu={(kind, anchor) => setMenu({ kind, anchor })} deck={{ threadId, path, onProblem: edits.setProblem }} />
            </SlideStage>
            <BelowStage ui={ui} slides={slides} srcOf={srcOf} edits={edits} arranging={arranging} />
            {!beside && properties}
          </div>
          {beside && properties}
        </div>
      )}
      <SlidesOverlays
        menu={menu}
        ui={ui}
        slides={slides}
        zoom={shownZoom}
        srcOf={srcOf}
        actions={{ open, download: (format) => downloads.download(format, index), history }}
        onCloseMenu={() => setMenu(null)}
        onStopped={() => rootRef.current?.focus()}
      />
    </div>
  );
}

/** Saves made in the panel, which redraw the deck, and what the last one found. */
function useEdits(threadId: string, path: string) {
  const [count, setCount] = useState(0);
  // Saves made outside the editor (notes, properties), after which it reads its slide again.
  const [outside, setOutside] = useState(0);
  const [problem, setProblem] = useState<string | null>(null);
  const saved = useCallback(() => setCount((n) => n + 1), []);
  const edit = (index: number, change: (doc: Document) => void) =>
    void editSlide(threadId, path, index, change).then(
      (done) => {
        setProblem(done.problems[0] ?? null);
        setCount((n) => n + 1);
        setOutside((n) => n + 1);
      },
      (e: unknown) => setProblem(e instanceof Error ? e.message : String(e)),
    );
  const loadSource = (index: number) => getSlideParts(threadId, path, index).then((read) => read.source);
  /** The deck changed as a whole (a slide added, moved, deleted): read it and its slides again. */
  const changed = (then: () => void) => {
    setCount((n) => n + 1);
    setOutside((n) => n + 1);
    then();
  };
  return { count, outside, problem, setProblem, saved, edit, loadSource, changed };
}

/** Over the slide: the editor, then the comments (`children`) above it. */
function SlideLayers({
  at,
  edits,
  refreshKey,
  children,
}: {
  at: { threadId: string; path: string; ui: ReturnType<typeof useSlidesUi>; zoom: number };
  edits: ReturnType<typeof useEdits>;
  refreshKey: string;
  children: ReactNode;
}) {
  return (
    <>
      {!at.ui.commenting && (
        <SlideEditing {...at} refreshKey={`${refreshKey}.${edits.outside}`} onSaved={edits.saved} onProblem={edits.setProblem} />
      )}
      {children}
    </>
  );
}

/** The slide's editor once the slide is clicked; before that, the click that starts it. */
function SlideEditing({
  threadId,
  path,
  ui,
  zoom,
  refreshKey,
  onSaved,
  onProblem,
}: {
  threadId: string;
  path: string;
  ui: ReturnType<typeof useSlidesUi>;
  zoom: number;
  refreshKey: string;
  onSaved: () => void;
  onProblem: (message: string | null) => void;
}) {
  if (!ui.editing) {
    return (
      <div
        aria-label="Edit the slide"
        className="absolute inset-0"
        onPointerDown={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          ui.startEditing({ x: (e.clientX - box.left) / zoom, y: (e.clientY - box.top) / zoom });
        }}
      />
    );
  }
  return (
    <SlideEditor
      key={ui.index}
      threadId={threadId}
      path={path}
      index={ui.index}
      zoom={zoom}
      refreshKey={refreshKey}
      firstPoint={ui.editing.index === ui.index ? ui.editing.point : null}
      onSaved={onSaved}
      onProblem={onProblem}
      onComment={ui.setCommentAt}
      onSelection={ui.setSelection}
      onMore={() => ui.setPropertiesShown(true)}
      insert={ui.insert}
      onInserted={ui.clearInsert}
      onExit={ui.stopEditing}
    />
  );
}

/** What floats over the stage: the toolbar, and the mini bar when the strip is hidden. */
function StageControls({
  ui,
  count,
  zoom,
  beside,
  busy,
  onMenu,
  deck,
}: {
  ui: ReturnType<typeof useSlidesUi>;
  count: number;
  zoom: number;
  beside: boolean;
  busy: boolean;
  onMenu: (kind: Menu["kind"], anchor: DOMRect) => void;
  deck: { threadId: string; path: string; onProblem: (message: string | null) => void };
}) {
  return (
    <>
      {ui.view === "slide" && (
        <SlideInsertBar {...deck} disabled={count === 0 || ui.commenting} onInsert={ui.requestInsert} />
      )}
      <SlideToolbar
        zoom={zoom}
        propertiesShown={ui.propertiesShown}
        beside={beside}
        onToggleProperties={() => ui.setPropertiesShown((shown) => !shown)}
        onZoomMenu={(anchor) => onMenu("zoom", anchor)}
        onPresentMenu={(anchor) => onMenu("present", anchor)}
        onDownloadMenu={(anchor) => onMenu("download", anchor)}
        busy={busy}
      />
      {ui.view === "slide" && !ui.stripShown && count > 0 && (
        <SlideMiniBar
          current={ui.index}
          count={count}
          notesShown={ui.notesShown}
          onGo={ui.go}
          onToggleNotes={ui.toggleNotes}
          onShowStrip={() => ui.setStripShown(true)}
        />
      )}
    </>
  );
}

function fitFor(view: SlidesView, stage: { width: number; height: number }): number {
  if (view === "slide") return fitZoom(stage.width - 2 * MARGIN, stage.height - TOOLBAR_ROOM - MARGIN);
  const columns = stage.width < 560 ? 2 : 3;
  return fitZoom((stage.width - 2 * MARGIN - (columns - 1) * CANVAS_GAP) / columns, Infinity);
}

function DeckNotices({ changed, error }: { changed: boolean; error: string | null }) {
  return (
    <>
      {changed && (
        <div className="shrink-0 border-t border-[var(--border)] px-4 py-1.5 text-xs text-[var(--warning)]">
          Shown as coscribe last built it; the file has changed since.
        </div>
      )}
      {error && (
        <div className="relative h-0 shrink-0">
          <div role="alert" className="absolute inset-x-3 top-1 z-20 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-[var(--danger)] shadow-md">
            {error}
          </div>
        </div>
      )}
    </>
  );
}

/** The panel's header, which the dock drags it by: the deck's name and menu, then the dock's controls. */
/** Under the stage: the slide's notes, then the bar and the thumbnail strip. */
function BelowStage({
  ui,
  slides,
  srcOf,
  edits,
  arranging,
}: {
  ui: ReturnType<typeof useSlidesUi>;
  slides: SlideInfo[];
  srcOf: (index: number) => string;
  edits: ReturnType<typeof useEdits>;
  arranging: ReturnType<typeof useSlideArranging>;
}) {
  const slide = slides[ui.index];
  const onNotes = (text: string) => edits.edit(ui.index, (doc) => setNotes(doc, text));
  return (
    <>
      {arranging.dialog && <NewSlideDialog layouts={arranging.dialog.layouts} onPick={arranging.pick} onClose={arranging.closeDialog} />}
      {arranging.menu && (
        <SlideMenu
          anchor={arranging.menu.anchor}
          label="Slide"
          width={210}
          align="left"
          entries={arranging.menuEntries(arranging.menu.index, slides.length)}
          onClose={() => arranging.setMenu(null)}
        />
      )}
      {ui.notesShown && ui.view === "slide" && slide && <SpeakerNotes key={`${slide.name}:${slide.notes}`} notes={slide.notes} onSave={onNotes} />}
      {(ui.view === "canvas" || ui.stripShown) && (
        <SlideFooter
          view={ui.view}
          notesShown={ui.notesShown}
          onView={ui.showView}
          onToggleNotes={ui.toggleNotes}
          onHideStrip={() => ui.setStripShown(false)}
          onNewSlide={() => arranging.openNew(ui.index)}
        >
          {ui.view === "slide" && (
            <SlideThumbnails
              slides={slides}
              current={ui.index}
              srcOf={srcOf}
              onSelect={ui.setCurrent}
              onMenu={(at, anchor) => arranging.setMenu({ index: at, anchor })}
              onMove={arranging.move}
            />
          )}
        </SlideFooter>
      )}
    </>
  );
}

function PanelTop({
  title,
  path,
  ui,
  onMenu,
}: {
  title: string;
  path: string;
  ui: ReturnType<typeof useSlidesUi>;
  onMenu: (kind: "title" | "comments", anchor: DOMRect) => void;
}) {
  const { commenting, toggleCommenting: onToggleComments } = ui;
  const dock = useDockPanel();
  const half = "flex h-7 items-center justify-center hover:bg-[var(--card-bg)]";
  return (
    <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
      <TitleButton title={title} path={path} onMenu={(anchor) => onMenu("title", anchor)} />
      <div className="flex-1" />
      <div
        className="flex items-center overflow-hidden rounded-lg border border-[var(--border)]"
        onPointerDown={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          title={commenting ? "Stop commenting (Esc)" : "Comment: click anything on the slide"}
          aria-label="Comment"
          aria-pressed={commenting}
          className={`${half} w-8 ${commenting ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`}
          onClick={onToggleComments}
        >
          <MessageCircleIcon className="h-4 w-4" />
        </button>
        <span className="h-4 border-l border-[var(--border)]" />
        <button
          type="button"
          title="Comment options"
          aria-label="Comment options"
          aria-haspopup="menu"
          className={`${half} w-6 text-[var(--muted)]`}
          onClick={(e) => onMenu("comments", e.currentTarget.getBoundingClientRect())}
        >
          <ChevronDownIcon className="h-3.5 w-3.5" />
        </button>
      </div>
      {dock.controls}
    </div>
  );
}

function TitleButton({ title, path, onMenu }: { title: string; path: string; onMenu: (anchor: DOMRect) => void }) {
  return (
    <button
      type="button"
      className="flex min-w-0 items-center gap-1 rounded-md px-1 py-0.5 text-[15px] hover:bg-[var(--card-bg)]"
      title={path}
      aria-haspopup="menu"
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => onMenu(e.currentTarget.getBoundingClientRect())}
    >
      <span className="truncate">{title}</span>
      <ChevronDownIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
    </button>
  );
}

/** The slide's speaker notes under it, written here; saved when the box loses focus. */
function SpeakerNotes({ notes, onSave }: { notes: string; onSave: (text: string) => void }) {
  const [text, setText] = useState(notes);
  return (
    <textarea
      aria-label="Speaker notes"
      placeholder="Add speaker notes"
      maxLength={4000}
      value={text}
      className="h-[120px] w-full shrink-0 resize-none border-t border-[var(--border)] bg-[var(--bg)] px-4 py-3 text-[15px] text-[var(--fg)] outline-none placeholder:text-[var(--muted)]"
      onChange={(e) => setText(e.target.value)}
      onBlur={() => text.trim() !== notes.trim() && onSave(text)}
    />
  );
}

/** Which slide, which view, and what is shown around it; the keys that change them. */
function useSlidesUi(count: number) {
  const [current, setCurrent] = useState(0);
  const [view, setView] = useState<SlidesView>("slide");
  const [stripShown, setStripShown] = useState(true);
  const [notesShown, setNotesShown] = useState(false);
  const [propertiesShown, setPropertiesShown] = useState(false);
  const [zoom, setZoom] = useState<number | null>(null);
  const [presenting, setPresenting] = useState<{ withNotes: boolean } | null>(null);
  const [commenting, setCommenting] = useState(false);
  const [showResolved, setShowResolved] = useState(false);
  // The slide where editing started and the click that started it, to select what was clicked.
  const [editing, setEditing] = useState<{ index: number; point: { x: number; y: number } | null } | null>(null);
  // An insert asked for from the toolbar, for the editor to add once the slide is read.
  const [insert, setInsert] = useState<{ what: Insert } | null>(null);
  const [commentAt, setCommentAt] = useState<CommentStart | null>(null);
  const [selection, setSelection] = useState<EditorSelection | null>(null);
  const index = Math.min(current, Math.max(count - 1, 0));
  const go = (delta: number) => setCurrent(Math.max(0, Math.min(count - 1, index + delta)));
  const showView = (next: SlidesView) => {
    setView(next);
    setZoom(null);
    if (next !== "slide") setEditing(null);
  };
  const openSlide = (i: number) => {
    setCurrent(i);
    showView("slide");
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>, shownZoom: number, step: (action: "undo" | "redo") => void) => {
    if (e.key === "Escape" && commenting) return setCommenting(false);
    const key = slideKey(e, view);
    if (key === null) return;
    e.preventDefault();
    if (key === "undo" || key === "redo") step(key);
    else if (typeof key === "number") go(key);
    else if (key === "fit") setZoom(null);
    else if (key === "in" || key === "out") setZoom(stepZoom(shownZoom, key === "in" ? 1 : -1));
    else if (key === "open") openSlide(index);
    else setCurrent(key === "first" ? 0 : count - 1);
  };
  const toggleNotes = () => setNotesShown((shown) => !shown);
  const stopPresenting = (last: number) => {
    setPresenting(null);
    setCurrent(last);
  };
  const toggleCommenting = () => {
    setCommenting((on) => !on);
    setEditing(null);
    showView("slide");
  };
  return {
    insert,
    requestInsert: (what: Insert) => {
      if (!editing) setEditing({ index, point: null });
      setInsert({ what });
    },
    clearInsert: () => setInsert(null),
    commentAt,
    setCommentAt,
    editing,
    startEditing: (point: { x: number; y: number }) => setEditing({ index, point }),
    stopEditing: () => setEditing(null),
    commenting,
    toggleCommenting,
    showResolved,
    setShowResolved,
    presenting,
    setPresenting,
    stopPresenting,
    index,
    view,
    zoom,
    stripShown,
    notesShown,
    propertiesShown,
    selection,
    setSelection,
    setCurrent,
    setZoom,
    setStripShown,
    setPropertiesShown,
    go,
    showView,
    openSlide,
    onKey,
    toggleNotes,
  };
}

function useSlideDeck(threadId: string, path: string, refreshKey: string) {
  const [deck, setDeck] = useState<SlideDeck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notBuilt, setNotBuilt] = useState(false);
  useEffect(() => {
    let live = true;
    getSlideDeck(threadId, path).then(
      (loaded) => {
        if (!live) return;
        setDeck(loaded);
        setError(null);
      },
      (e: unknown) => {
        if (!live) return;
        if (e instanceof DeckNotBuilt) setNotBuilt(true);
        else setError(e instanceof Error ? e.message : String(e));
      },
    );
    return () => {
      live = false;
    };
  }, [threadId, path, refreshKey]);
  const open = (reveal: boolean) => void openThreadFile(threadId, path, reveal).then((e) => e && setError(e));
  const srcOf = useCallback((i: number) => slideImageUrl(threadId, path, i, refreshKey), [threadId, path, refreshKey]);
  return { deck, error, notBuilt, open, srcOf };
}

function useSizes(rootRef: React.RefObject<HTMLDivElement | null>, stageRef: React.RefObject<HTMLDivElement | null>, ready: boolean) {
  const [stage, setStage] = useState({ width: 0, height: 0 });
  const [panelWidth, setPanelWidth] = useState(0);
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      const box = stageRef.current?.getBoundingClientRect();
      if (box) setStage({ width: box.width, height: box.height });
      setPanelWidth(rootRef.current?.getBoundingClientRect().width ?? 0);
    });
    if (stageRef.current) observer.observe(stageRef.current);
    if (rootRef.current) observer.observe(rootRef.current);
    return () => observer.disconnect();
  }, [rootRef, stageRef, ready]);
  return { stage, panelWidth };
}

type SlideKey = "in" | "out" | "fit" | "first" | "last" | "open" | "undo" | "redo" | 1 | -1;

/** What a key does in the panel; nothing while typing in a field. */
function slideKey(e: KeyboardEvent<HTMLDivElement>, view: SlidesView): SlideKey | null {
  if ((e.target as HTMLElement).closest("input, textarea, [contenteditable]")) return null;
  if (e.ctrlKey || e.metaKey) {
    const letter = e.key.toLowerCase();
    if (letter === "z") return e.shiftKey ? "redo" : "undo";
    if (letter === "y") return "redo";
    return ({ "=": "in", "+": "in", "-": "out", "0": "fit" } as const)[e.key as "=" | "+" | "-" | "0"] ?? null;
  }
  if (["ArrowRight", "ArrowDown", "PageDown"].includes(e.key)) return 1;
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) return -1;
  if (e.key === "Home") return "first";
  if (e.key === "End") return "last";
  if (e.key === "Enter" && view === "canvas") return "open";
  return null;
}

/** The open menu, and the presenter over the whole panel. */
function SlidesOverlays({
  menu,
  ui,
  slides,
  zoom,
  srcOf,
  actions,
  onCloseMenu,
  onStopped,
}: {
  menu: Menu | null;
  ui: ReturnType<typeof useSlidesUi>;
  slides: SlideInfo[];
  zoom: number;
  srcOf: (index: number) => string;
  actions: Pick<MenuActions, "open" | "download" | "history">;
  onCloseMenu: () => void;
  /** Presenting ended, back on the panel. */
  onStopped: () => void;
}) {
  const { presenting, index } = ui;
  const [askingDiscard, setAskingDiscard] = useState(false);
  const menuEntries = (kind: Menu["kind"]) =>
    entriesFor(kind, zoom, ui.view, {
      ...actions,
      ui,
      setZoom: ui.setZoom,
      present: (withNotes) => ui.setPresenting({ withNotes }),
      askDiscard: () => setAskingDiscard(true),
    });
  const onStopPresenting = (last: number) => {
    ui.stopPresenting(last);
    onStopped();
  };
  return (
    <>
      {menu && (
        <SlideMenu
          anchor={menu.anchor}
          label={MENU_LABELS[menu.kind]}
          width={menu.kind === "zoom" ? 210 : menu.kind === "download" ? 280 : 240}
          entries={menuEntries(menu.kind)}
          onClose={onCloseMenu}
        />
      )}
      {askingDiscard && (
        <ConfirmDialog
          title="Discard my edits?"
          description="Every change you made since coscribe's last version of this presentation is taken back."
          confirmLabel="Discard"
          onCancel={() => setAskingDiscard(false)}
          onConfirm={() => {
            setAskingDiscard(false);
            actions.history.step("discard");
          }}
        />
      )}
      {presenting && slides.length > 0 && (
        <SlidePresenter slides={slides} start={index} withNotes={presenting.withNotes} srcOf={srcOf} onExit={onStopPresenting} />
      )}
    </>
  );
}

interface MenuActions {
  setZoom: (zoom: number | null) => void;
  history: ReturnType<typeof useSlideHistory>;
  present: (withNotes: boolean) => void;
  open: (reveal: boolean) => void;
  download: (format: SlideExport) => void;
  ui: ReturnType<typeof useSlidesUi>;
  askDiscard: () => void;
}

function entriesFor(kind: Menu["kind"], zoom: number, view: SlidesView, actions: MenuActions): MenuEntry[] {
  if (kind === "zoom") return zoomEntries(zoom, view, actions.setZoom, actions.history);
  if (kind === "download") return downloadEntries(actions.download);
  if (kind === "comments") return commentEntries(actions.ui);
  return kind === "present" ? presentEntries(actions.present) : titleEntries(actions.open, actions.history, actions.askDiscard);
}

function commentEntries(ui: ReturnType<typeof useSlidesUi>): MenuEntry[] {
  return [
    { label: ui.commenting ? "Stop commenting" : "Comment on the slide", onSelect: ui.toggleCommenting },
    { label: "Show resolved comments", checked: ui.showResolved, onSelect: () => ui.setShowResolved((shown) => !shown) },
  ];
}

const MENU_LABELS: Record<Menu["kind"], string> = {
  zoom: "Zoom",
  title: "Presentation",
  present: "Present",
  download: "Download",
  comments: "Comments",
};

/** One download at a time: made (on the server, or drawn here for a PNG), then saved. */
function useSlideDownloads(threadId: string, path: string, srcOf: (index: number) => string) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const download = (format: SlideExport, index: number) => {
    setBusy(true);
    setFailed(null);
    slideExport(threadId, path, format, index, srcOf(index))
      .then(({ blob, name }) => saveBlob(blob, name))
      .catch((e: unknown) => setFailed(`The download failed: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => setBusy(false));
  };
  return { busy, failed, download };
}

function NotBuilt({ name, onOpen }: { name: string; onOpen: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-[var(--stage-bg)] p-6 text-center">
      <p className="max-w-[360px] text-sm text-[var(--muted)]">
        {name} was not made by coscribe from slide pages, so it can't be shown here yet.
      </p>
      <button
        type="button"
        className="flex h-9 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 text-sm hover:bg-[var(--card-bg)]"
        onClick={onOpen}
      >
        <ExternalLinkIcon className="h-4 w-4" />
        Open in PowerPoint
      </button>
    </div>
  );
}
