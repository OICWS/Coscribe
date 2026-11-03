import { useEffect, useRef, useState } from "react";
import { styleChanges, treeRows, type ElementChange, type InspectedElement, type InspectedNode } from "../../lib/boardInspector";
import { CloseIcon, UndoIcon } from "../icons";
import { ElementProperties } from "./ElementProperties";

type Tab = "properties" | "code";

const OWN = "style attribute";

/** The element's own style, typed as CSS: written into its style attribute when the field is left
 * or Ctrl+Enter is pressed. A rule of a style sheet can style many elements, so it only reads. */
function OwnStyle({ element, onEdit }: { element: InspectedElement; onEdit: (change: ElementChange) => void }) {
  const own = element.rules.find((rule) => rule.selector === OWN)?.declarations ?? [];
  const text = own.map(([name, value]) => `${name}: ${value};`).join("\n");
  const [draft, setDraft] = useState(text);
  const commit = () => {
    const style = styleChanges(own, draft);
    if (Object.keys(style).length) onEdit({ style });
  };
  return (
    <div>
      <div className="text-[var(--muted)]">This element</div>
      <textarea
        aria-label="This element's style"
        value={draft}
        placeholder="color: var(--brand);"
        rows={Math.max(3, own.length + 1)}
        spellCheck={false}
        className="mt-1 w-full resize-y rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 font-mono text-[12px] focus:border-[var(--accent)] focus:outline-none"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) e.currentTarget.blur();
          if (e.key === "Escape") setDraft(text);
        }}
      />
    </div>
  );
}

function Code({ element, onEdit }: { element: InspectedElement; onEdit: (change: ElementChange) => void }) {
  const sheets = element.rules.filter((rule) => rule.selector !== OWN);
  return (
    // Keyed by the element and its own style, so the field shows the page again after a save.
    <div key={`${element.path}|${JSON.stringify(element.rules.find((rule) => rule.selector === OWN))}`} className="space-y-3 px-3 py-2 font-mono text-[12px] leading-relaxed">
      <OwnStyle element={element} onEdit={onEdit} />
      {sheets.length === 0 && <p className="font-sans text-[13px] text-[var(--muted)]">No style rule matches this element.</p>}
      {sheets.map((rule, i) => (
        <div key={i}>
          <div className="text-[var(--muted)]">{rule.selector}</div>
          {rule.declarations.map(([name, value]) => (
            <div key={name} className="pl-3">
              {name}: {value};
            </div>
          ))}
        </div>
      ))}
      {element.inherited.map((group) => (
        <div key={group.from}>
          <div className="font-sans text-[13px] text-[var(--muted)]">From &lt;{group.from}&gt;</div>
          {group.props.map(([name, value]) => (
            <div key={name} className="pl-3">
              {name}: {value};
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function Tree({ tree, selected, onSelect }: { tree: InspectedNode; selected: string | null; onSelect: (path: string) => void }) {
  const list = useRef<HTMLDivElement>(null);
  // A block body: scrollIntoView returns a promise in newer browsers, and React would call it as the cleanup.
  useEffect(() => {
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selected]);
  return (
    <div ref={list} role="tree" aria-label="Elements" className="max-h-[40%] shrink-0 overflow-auto border-b border-[var(--border)] py-1">
      {treeRows(tree).map(({ node, depth }) => (
        <button
          key={node.path}
          type="button"
          role="treeitem"
          aria-selected={node.path === selected}
          className={`flex w-full items-center gap-1.5 py-1 pr-2 text-left text-[13px] ${node.path === selected ? "bg-[var(--card-bg)] font-medium" : "hover:bg-[var(--card-bg)]"}`}
          style={{ paddingLeft: 10 + depth * 14 }}
          onClick={() => onSelect(node.path)}
        >
          <span className="shrink-0">{node.path === "" ? "Page" : node.kind}</span>
          {node.text && <span className="min-w-0 truncate text-[var(--muted)]">“{node.text}”</span>}
        </button>
      ))}
    </div>
  );
}

/** Beside the canvas: the selected artboard's elements as a tree, and for the element picked
 * there or on the board, what it measures and the style that makes it so, which the Properties tab
 * also edits. */
export function BoardInspector({
  boardTitle,
  tree,
  element,
  problem,
  onSelect,
  onEdit,
  canUndo,
  onUndo,
  onClose,
}: {
  boardTitle: string | null;
  tree: InspectedNode | null;
  element: InspectedElement | null;
  problem: string | null;
  onSelect: (path: string) => void;
  onEdit: (change: ElementChange) => void;
  canUndo: boolean;
  onUndo: () => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("properties");
  // Ctrl+Z in a field undoes typing there; elsewhere it undoes the panel's last edit to the page.
  useEffect(() => {
    if (!canUndo) return;
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.key.toLowerCase() !== "z") return;
      if (e.target instanceof HTMLElement && e.target.closest("input, textarea, [contenteditable]")) return;
      e.preventDefault();
      onUndo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canUndo, onUndo]);
  const tabButton = (id: Tab, label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={tab === id}
      className={`h-7 rounded-md px-2.5 text-[13px] ${tab === id ? "bg-[var(--card-bg)] font-medium" : "text-[var(--muted)] hover:text-[var(--text)]"}`}
      onClick={() => setTab(id)}
    >
      {label}
    </button>
  );
  return (
    <aside aria-label="Properties" className="flex w-80 shrink-0 flex-col border-l border-[var(--border)] bg-[var(--panel-bg)]">
      <div className="flex h-11 shrink-0 items-center gap-1 border-b border-[var(--border)] px-2" role="tablist">
        {tabButton("properties", "Properties")}
        {tabButton("code", "Code")}
        <div className="flex-1" />
        <button
          type="button"
          aria-label="Undo"
          title="Undo the last edit (Ctrl+Z)"
          disabled={!canUndo}
          className="rounded-md p-1 text-[var(--muted)] hover:bg-[var(--card-bg)] disabled:opacity-40 disabled:hover:bg-transparent"
          onClick={onUndo}
        >
          <UndoIcon className="h-4 w-4" />
        </button>
        <button type="button" aria-label="Close properties" className="rounded-md p-1 text-[var(--muted)] hover:bg-[var(--card-bg)]" onClick={onClose}>
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
      {!boardTitle ? (
        <p className="p-3 text-[13px] text-[var(--muted)]">Select an artboard to see its elements.</p>
      ) : (
        <>
          {tree ? <Tree tree={tree} selected={element?.path ?? null} onSelect={onSelect} /> : <p className="p-3 text-[13px] text-[var(--muted)]">Reading {boardTitle}…</p>}
          <div className="min-h-0 flex-1 overflow-auto">
            {!element ? (
              <p className="p-3 text-[13px] text-[var(--muted)]">Click an element on the artboard, or pick one above.</p>
            ) : (
              <>
                <div className="truncate px-3 pt-2 font-mono text-[12px] text-[var(--muted)]">
                  &lt;{element.label}&gt;{element.text && <span className="font-sans"> “{element.text}”</span>}
                </div>
                {tab === "properties" ? <ElementProperties element={element} problem={problem} onEdit={onEdit} /> : <Code element={element} onEdit={onEdit} />}
              </>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
