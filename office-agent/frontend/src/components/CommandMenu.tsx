import type { useCommandMenu } from "../lib/useCommandMenu";

type Menu = ReturnType<typeof useCommandMenu>;

/** The "/" menu: names only, so a long description cannot widen the list or wrap a row; the
 * highlighted command's description shows beside it. */
export function CommandMenu({ menu, onPick }: { menu: Menu; onPick: (index: number) => void }) {
  const current = menu.matches[menu.index];
  return (
    <div className="absolute bottom-full left-0 z-20 mb-1 flex items-start">
      <div
        ref={menu.listRef}
        role="listbox"
        onScroll={menu.placeTip}
        className="max-h-72 w-56 overflow-y-auto rounded-[14px] border border-[var(--border)] bg-[var(--bg)] p-1 shadow-[var(--shadow)]"
      >
        {menu.matches.map((cmd, i) => (
          <div
            key={cmd.name}
            ref={menu.itemRef(i)}
            role="option"
            aria-selected={i === menu.index}
            className={`truncate rounded-lg px-2.5 py-1.5 text-sm ${i === menu.index ? "bg-[var(--card-bg)]" : ""}`}
            onMouseEnter={() => menu.setIndex(i)}
            onMouseDown={(e) => {
              e.preventDefault();
              onPick(i);
            }}
          >
            {cmd.name}
          </div>
        ))}
      </div>
      {current?.description && (
        <div
          role="tooltip"
          style={{ top: menu.tipTop }}
          className="absolute left-[calc(14rem+0.5rem)] mt-1 w-max max-w-72 rounded-md bg-[var(--fg)] px-2 py-1 text-xs leading-snug text-[var(--bg)]"
        >
          <span className="line-clamp-3">{current.description}</span>
        </div>
      )}
    </div>
  );
}

/** What a "/" typed during a reply gets instead of the menu: commands wait for the reply. */
export function CommandsAfterReply() {
  return (
    <div role="status" className="absolute bottom-full left-0 z-20 mb-1 rounded-[10px] border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-[var(--muted)] shadow-[var(--shadow)]">
      Commands are available once this reply finishes.
    </div>
  );
}
