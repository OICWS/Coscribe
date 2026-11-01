import { useEffect, useRef, useState } from "react";
import { treeRows, type InspectedElement, type InspectedNode } from "../../lib/boardInspector";
import { CloseIcon } from "../icons";

type Tab = "properties" | "code";

const SECTIONS: [string, [string, string][]][] = [
  [
    "Layout",
    [
      ["display", "Display"],
      ["position", "Position"],
      ["flex-direction", "Direction"],
      ["justify-content", "Justify"],
      ["align-items", "Align"],
      ["gap", "Gap"],
      ["padding", "Padding"],
      ["margin", "Margin"],
    ],
  ],
  [
    "Text",
    [
      ["font-family", "Font"],
      ["font-size", "Size"],
      ["font-weight", "Weight"],
      ["line-height", "Line height"],
      ["color", "Color"],
    ],
  ],
  [
    "Fill",
    [
      ["background-color", "Background"],
      ["border-radius", "Radius"],
      ["opacity", "Opacity"],
    ],
  ],
];

// Values that say nothing about the element: a reader scans what was set, not every default.
const SAYS_NOTHING = new Set(["", "normal", "none", "0px", "static", "rgba(0, 0, 0, 0)", "1", "auto"]);

function Row({ label, value }: { label: string; value: string }) {
  const colour = /^(rgb|#)/.test(value) ? value : null;
  return (
    <div className="flex items-center gap-2 py-1 text-[13px]">
      <span className="w-24 shrink-0 text-[var(--muted)]">{label}</span>
      {colour && <span className="h-3.5 w-3.5 shrink-0 rounded border border-[var(--border)]" style={{ background: colour }} />}
      <span className="min-w-0 flex-1 truncate" title={value}>
        {value}
      </span>
    </div>
  );
}

function Properties({ element }: { element: InspectedElement }) {
  return (
    <div className="divide-y divide-[var(--border)]">
      <section className="px-3 py-2">
        <h3 className="mb-1 text-[13px] font-semibold">Size</h3>
        <Row label="Width" value={`${Math.round(element.box.width)}px`} />
        <Row label="Height" value={`${Math.round(element.box.height)}px`} />
      </section>
      {SECTIONS.map(([title, fields]) => {
        const shown = fields.filter(([name]) => !SAYS_NOTHING.has(element.computed[name] ?? ""));
        if (!shown.length) return null;
        return (
          <section key={title} className="px-3 py-2">
            <h3 className="mb-1 text-[13px] font-semibold">{title}</h3>
            {shown.map(([name, label]) => (
              <Row key={name} label={label} value={element.computed[name]} />
            ))}
          </section>
        );
      })}
    </div>
  );
}

function Code({ element }: { element: InspectedElement }) {
  return (
    <div className="space-y-3 px-3 py-2 font-mono text-[12px] leading-relaxed">
      {element.rules.length === 0 && <p className="font-sans text-[13px] text-[var(--muted)]">No style rule matches this element.</p>}
      {element.rules.map((rule, i) => (
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
  useEffect(() => list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" }), [selected]);
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
 * there or on the board, what it measures and the style that makes it so. It only reads. */
export function BoardInspector({
  boardTitle,
  tree,
  element,
  onSelect,
  onClose,
}: {
  boardTitle: string | null;
  tree: InspectedNode | null;
  element: InspectedElement | null;
  onSelect: (path: string) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("properties");
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
                {tab === "properties" ? <Properties element={element} /> : <Code element={element} />}
              </>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
