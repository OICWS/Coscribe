import { type ComponentType, type SVGProps, useRef, useState } from "react";
import type { ConnectorTool, ConnectorToolPolicy } from "../../../types/settings";
import { BanIcon, CheckCircleIcon, CheckIcon, ChevronDownIcon, HandIcon } from "../../icons";
import { useClickOutside } from "../../../lib/useClickOutside";

const POLICIES: {
  value: ConnectorToolPolicy;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}[] = [
  { value: "allow", label: "Always allow", icon: CheckCircleIcon },
  { value: "ask", label: "Needs approval", icon: HandIcon },
  { value: "block", label: "Blocked", icon: BanIcon },
];

/** Three icon buttons, one per policy, for a single tool. */
function PolicyToggle({
  tool,
  onChange,
}: {
  tool: ConnectorTool;
  onChange: (policy: ConnectorToolPolicy) => void;
}) {
  return (
    <div role="radiogroup" aria-label={`${tool.title} permission`} className="flex shrink-0 rounded-lg bg-[var(--card-bg)] p-0.5">
      {POLICIES.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={tool.policy === value}
          aria-label={label}
          title={label}
          className={`flex h-7 w-8 items-center justify-center rounded-md ${
            tool.policy === value
              ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm ring-1 ring-[var(--border)]"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
          onClick={() => onChange(value)}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  );
}

/** Sets every tool in a group at once; shows the group's policy when its
 * tools agree. */
function GroupPolicyMenu({
  tools,
  onChange,
}: {
  tools: ConnectorTool[];
  onChange: (policy: ConnectorToolPolicy) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  const shared = tools.every((t) => t.policy === tools[0]?.policy) ? tools[0]?.policy : undefined;
  const current = POLICIES.find((p) => p.value === shared);
  const Icon = current?.icon;
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-9 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm hover:bg-[var(--card-bg)]"
        onClick={() => setOpen((v) => !v)}
      >
        {Icon && <Icon className="h-4 w-4" />}
        {current?.label ?? "Custom"}
        <ChevronDownIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-1 min-w-44 rounded-[10px] border border-[var(--border)] bg-[var(--panel-bg)] py-1 shadow-[var(--shadow)]"
        >
          {POLICIES.map(({ value, label, icon: ItemIcon }) => (
            <button
              key={value}
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-[var(--card-bg)]"
              onClick={() => {
                setOpen(false);
                onChange(value);
              }}
            >
              <ItemIcon className="h-4 w-4" />
              <span className="flex-1">{label}</span>
              {shared === value && <CheckIcon className="h-3.5 w-3.5" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ToolGroup({
  title,
  tools,
  onChange,
}: {
  title: string;
  tools: ConnectorTool[];
  onChange: (policies: Record<string, ConnectorToolPolicy>) => void;
}) {
  const [open, setOpen] = useState(true);
  if (tools.length === 0) return null;
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-3 py-2">
        <button
          type="button"
          aria-expanded={open}
          className="flex flex-1 items-center gap-2 text-left text-[15px]"
          onClick={() => setOpen((v) => !v)}
        >
          <ChevronDownIcon className={`h-4 w-4 text-[var(--muted)] transition-transform ${open ? "" : "-rotate-90"}`} />
          {title}
          <span className="rounded-md bg-[var(--card-bg)] px-1.5 text-xs text-[var(--muted)]">{tools.length}</span>
        </button>
        <GroupPolicyMenu
          tools={tools}
          onChange={(policy) => onChange(Object.fromEntries(tools.map((t) => [t.name, policy])))}
        />
      </div>
      {open && (
        <div className="flex flex-col divide-y divide-[var(--border)] pl-6">
          {tools.map((tool) => (
            <div key={tool.name} className="flex items-center gap-6 py-3">
              <div className="min-w-0 flex-1">
                <div className="text-sm">{tool.title}</div>
                {tool.description && tool.description !== tool.title && (
                  <div className="mt-0.5 line-clamp-2 text-[13px] text-[var(--muted)]">{tool.description}</div>
                )}
              </div>
              <PolicyToggle tool={tool} onChange={(policy) => onChange({ [tool.name]: policy })} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
