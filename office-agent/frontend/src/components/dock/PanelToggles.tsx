import { useState } from "react";
import type { PanelId } from "../../lib/dockLayout";
import { showArtifacts } from "../../lib/nav";
import { CONVERSATION_ITEMS, type ToolbarItem } from "../../lib/toolbarItems";
import { DRAWS_TITLE_BAR, TITLE_BAR_ICON } from "../../lib/titleBar";
import { ArtifactsIcon } from "../artifacts/artifactIcons";
import { BrowserIcon, ListChecksIcon, PanelRightIcon, SidebarIcon, SubAgentsIcon } from "../icons";
import { ToolbarDialog, ToolbarMenu, type ToolbarEntry } from "./ToolbarMenu";

const on = "bg-[var(--accent-soft)] text-[var(--accent-ink)]";

/** The bar's items, in the title bar beside Settings (desktop) or at the right end of the page's
 * header: the pinned ones as buttons, the others in the menu behind the arrow. A panel in a window
 * of its own counts as open; its switch brings that window to the front. The sidebar's own button
 * stays at the left end of the bar, and shows only while the sidebar is pinned. */
export function PanelToggles({
  open,
  onToggle,
  inConversation,
  pinned,
  onPinnedChange,
  sidebar,
  artifactsOpen,
  backgroundTitle,
  running,
  waiting,
}: {
  open: (panel: PanelId) => boolean;
  onToggle: (panel: PanelId) => void;
  /** Panels belong to a conversation; elsewhere only the other items are offered. */
  inConversation: boolean;
  pinned: readonly ToolbarItem[];
  onPinnedChange: (pinned: ToolbarItem[]) => void;
  sidebar: { open: boolean; toggle: () => void };
  artifactsOpen: boolean;
  backgroundTitle: string;
  running: number;
  waiting: number;
}) {
  const [editing, setEditing] = useState(false);
  const task = open("task");
  const background = open("background");
  const entries: ToolbarEntry[] = [
    { id: "sidebar", label: "Sidebar", menuLabel: sidebar.open ? "Hide sidebar" : "Show sidebar", Icon: SidebarIcon, active: sidebar.open, onSelect: sidebar.toggle },
    { id: "artifacts", label: "Artifacts", Icon: ArtifactsIcon, active: artifactsOpen, onSelect: showArtifacts },
    { id: "task", label: "Task details", title: task ? "Hide task details" : "Show task details", Icon: PanelRightIcon, active: task, onSelect: () => onToggle("task") },
    { id: "plan", label: "Plan", Icon: ListChecksIcon, active: open("plan"), onSelect: () => onToggle("plan") },
    { id: "browser", label: "Browser", Icon: BrowserIcon, active: open("browser"), onSelect: () => onToggle("browser") },
    {
      id: "background",
      label: backgroundTitle,
      Icon: SubAgentsIcon,
      active: background,
      onSelect: () => onToggle("background"),
      badge: running > 0 && (
        <span
          aria-label={waiting > 0 ? `${running} running, ${waiting} waiting for you` : `${running} running`}
          className={`flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-medium leading-none ${
            waiting > 0 ? "bg-[var(--warning)] text-[var(--bg)]" : "bg-[var(--accent)] text-[var(--accent-fg)]"
          }`}
        >
          {running}
        </span>
      ),
    },
  ];
  const offered = entries.filter((e) => inConversation || !CONVERSATION_ITEMS.includes(e.id));
  const icon = DRAWS_TITLE_BAR ? TITLE_BAR_ICON : { className: "h-[18px] w-[18px]" };
  const off = DRAWS_TITLE_BAR
    ? "text-[var(--fg)] hover:bg-[var(--card-bg)]"
    : "text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
  return (
    <>
      {offered
        .filter((e) => e.id !== "sidebar" && pinned.includes(e.id))
        .map(({ id, label, title, Icon, active, onSelect, badge }) => (
          <button
            key={id}
            type="button"
            title={title ?? label}
            aria-pressed={active}
            className={`relative flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${active ? on : off}`}
            onClick={onSelect}
          >
            <Icon {...icon} />
            {badge && <span className="absolute -right-0.5 -top-0.5 motion-safe:animate-pulse">{badge}</span>}
          </button>
        ))}
      <ToolbarMenu entries={offered.filter((e) => !pinned.includes(e.id))} onEdit={() => setEditing(true)} />
      {editing && <ToolbarDialog entries={entries} pinned={pinned} onChange={onPinnedChange} onClose={() => setEditing(false)} />}
    </>
  );
}
