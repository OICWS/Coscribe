import type { KeyboardEvent, MouseEvent } from "react";
import { editedLabel, type PageItem } from "../../lib/artifacts";
import { MoreIcon } from "../icons";
import { PinIcon } from "./artifactIcons";
import { KindTile, Thumbnail } from "./ArtifactThumb";

interface ItemProps {
  item: PageItem;
  pinned: boolean;
  now: Date;
  onOpen: () => void;
  /** The item's menu, under the button that asked for it. */
  onMenu: (anchor: DOMRect) => void;
}

/** A card or row opens on a click or Enter; its menu button is a control of its own inside it. */
const asLink = (item: PageItem, onOpen: () => void) => ({
  role: "button",
  tabIndex: 0,
  "aria-label": `Open ${item.name}`,
  onClick: onOpen,
  onKeyDown: (e: KeyboardEvent) => {
    if (e.key === "Enter" && e.target === e.currentTarget) onOpen();
  },
});

function MenuButton({ item, onMenu, className }: { item: PageItem; onMenu: (anchor: DOMRect) => void; className: string }) {
  return (
    <button
      type="button"
      aria-label={`Options for ${item.name}`}
      aria-haspopup="menu"
      className={`flex h-8 w-8 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)] focus-visible:opacity-100 ${className}`}
      onClick={(e: MouseEvent<HTMLButtonElement>) => {
        e.stopPropagation();
        onMenu(e.currentTarget.getBoundingClientRect());
      }}
    >
      <MoreIcon className="h-[18px] w-[18px]" />
    </button>
  );
}

/** The grid layout's card: the thumbnail, the kind's mark across its lower edge, the name and when
 * it was last changed. */
export function ArtifactCard({ item, pinned, now, onOpen, onMenu }: ItemProps) {
  return (
    <div
      {...asLink(item, onOpen)}
      className="group relative cursor-pointer rounded-2xl border border-[var(--border)] bg-[var(--bg)] transition-colors hover:border-[var(--border-hover)] focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
    >
      <div className="relative">
        <div className="overflow-hidden rounded-t-2xl">
          <Thumbnail item={item} />
        </div>
        <span className="absolute -bottom-4 left-3 rounded-xl bg-[var(--bg)] ring-1 ring-[var(--border)]">
          <KindTile kind={item.kind} size="md" />
        </span>
      </div>
      <div className="px-4 pb-4 pt-7">
        <div className="truncate text-[17px] font-medium" title={item.name}>
          {item.name}
        </div>
        <div className="mt-1.5 flex items-center gap-2 text-sm text-[var(--muted)]">
          <span className="truncate">{editedLabel(item.modified_at, now)}</span>
          {pinned && <PinIcon filled className="h-3.5 w-3.5 shrink-0 text-[var(--accent)]" />}
        </div>
      </div>
      <MenuButton item={item} onMenu={onMenu} className="absolute right-3 top-3 bg-[var(--bg)]/90 opacity-0 shadow-sm ring-1 ring-[var(--border)] group-hover:opacity-100" />
    </div>
  );
}

/** The list layout's row. */
export function ArtifactRow({ item, pinned, now, onOpen, onMenu }: ItemProps) {
  return (
    <div
      {...asLink(item, onOpen)}
      className="group flex cursor-pointer items-center gap-4 rounded-xl px-3 py-2.5 hover:bg-[var(--card-bg)] focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
    >
      <KindTile kind={item.kind} size="lg" />
      <span className="min-w-0 flex-1 truncate text-[17px]" title={item.name}>
        {item.name}
      </span>
      {pinned && <PinIcon filled className="h-4 w-4 shrink-0 text-[var(--accent)]" />}
      <span className="hidden shrink-0 text-sm text-[var(--muted)] sm:block">{editedLabel(item.modified_at, now)}</span>
      <MenuButton item={item} onMenu={onMenu} className="" />
    </div>
  );
}
