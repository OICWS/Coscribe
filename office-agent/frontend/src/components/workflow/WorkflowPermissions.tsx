import { type ReactNode, useEffect, useState } from "react";
import { getWorkflowPermissions, type PermissionsResult, type WorkflowAgentPermissions } from "../../lib/rest";
import { toolLabel } from "../../lib/toolLabels";
import { AUTONOMY_LABEL } from "../../lib/workflowLabels";
import type { Workflow } from "../../types/workflow";
import { AlertCircleIcon, FolderIcon, GlobeIcon, TerminalIcon } from "../icons";
import { TargetIcon } from "./parts";

interface Props {
  workflow: Workflow;
  /** A saved task: what its runs were allowed since counts too. */
  triggerId?: string;
  /** Mark what this version adds to the task's saved one. */
  againstSaved?: boolean;
  /** Changes when something was allowed since, so the list is read again. */
  version?: string;
  className?: string;
}

function New() {
  return (
    <span className="ml-1.5 rounded-full bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--fg)]">
      New
    </span>
  );
}

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 px-3.5 py-2.5">
      <span className="mt-0.5 h-4 w-4 shrink-0 text-[var(--muted)]">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium">{label}</div>
        <div className="mt-0.5 text-[13px] text-[var(--muted)]">{children}</div>
      </div>
    </div>
  );
}

function List({ items, fresh }: { items: string[]; fresh: string[] }) {
  return (
    <>
      {items.map((item, index) => (
        <span key={item} className="break-all">
          {index > 0 && ", "}
          <span className="text-[var(--fg)]">{item}</span>
          {fresh.includes(item) && <New />}
        </span>
      ))}
    </>
  );
}

function AgentLine({ agent, fresh }: { agent: WorkflowAgentPermissions; fresh: boolean }) {
  const reach =
    agent.autonomy === "bounded"
      ? `can use ${agent.tools.map(toolLabel).join(", ")}`
      : "can use any of Coscribe’s tools, under this task’s approval setting";
  const places = [
    agent.folders.length > 0 ? `change files in ${agent.folders.join(", ")}` : "",
    agent.sites.length > 0 ? `open ${agent.sites.join(", ")}` : "",
  ].filter(Boolean);
  return (
    <div>
      <span className="text-[var(--fg)]">{agent.title}</span>
      {fresh && <New />}
      <span>
        {" "}
        · {AUTONOMY_LABEL[agent.autonomy]}: {reach}
        {places.length > 0 && `, ${places.join(", ")}`}; at most {agent.max_steps} model calls.
      </span>
      {agent.read_only && <span> It only reads, because what it’s given comes from outside.</span>}
    </div>
  );
}

/** What a workflow will be able to do once saved -- saving is the consent,
 * and a run that needs more stops and asks. Plain about what scripts are:
 * checked for where they write, not contained. */
export function WorkflowPermissions({
  workflow,
  triggerId,
  againstSaved = false,
  version = "",
  className = "mt-5",
}: Props) {
  const [result, setResult] = useState<PermissionsResult | null>(null);
  const key = JSON.stringify(workflow);

  useEffect(() => {
    let current = true;
    getWorkflowPermissions(workflow, triggerId, againstSaved).then((next) => {
      if (current && !("error" in next)) setResult(next);
    });
    return () => {
      current = false;
    };
    // The workflow's content, not its identity, decides when to ask again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, triggerId, againstSaved, version]);

  if (!result) return null;
  const { permissions: p, added } = result;
  const fresh = {
    sites: added?.sites ?? [],
    folders: added?.folders ?? [],
    scripts: added?.scripts ?? [],
    notable: added?.notable.map((n) => n.tool) ?? [],
    agents: added?.agents?.map((a) => a.title) ?? [],
  };
  return (
    <section
      aria-label="Permissions"
      data-testid="workflow-permissions"
      className={`overflow-hidden rounded-xl border border-[var(--border)] ${className}`}
    >
      <div className="border-b border-[var(--border)] bg-[var(--card-bg)] px-3.5 py-2.5">
        <div className="text-sm font-medium">What this workflow can do</div>
        <div className="text-[13px] text-[var(--muted)]">
          Saving allows exactly this. Anything else makes a run stop and ask you first.
        </div>
      </div>
      <div className="divide-y divide-[var(--border)]">
        <Row icon={<GlobeIcon className="h-4 w-4" />} label="Websites">
          {p.sites.length > 0 ? <List items={p.sites} fresh={fresh.sites} /> : "None named in its steps."}
          {p.sites_at_run_time.length > 0 && (
            <div>Decided at run time in: {p.sites_at_run_time.join(", ")}. Those stop and ask.</div>
          )}
        </Row>
        <Row icon={<FolderIcon className="h-4 w-4" />} label="Folders it can change">
          Its workspace
          {p.folders.length > 0 && (
            <>
              , and <List items={p.folders} fresh={fresh.folders} />
            </>
          )}
        </Row>
        {p.scripts.length > 0 && (
          <Row icon={<TerminalIcon className="h-4 w-4" />} label="Runs scripts">
            <List items={p.scripts} fresh={fresh.scripts} />
            <div>
              Scripts aren’t sandboxed: they can read any file this app can and use the network. They’re checked so
              they only write in the folders above, which guards against mistakes, not against harm.
            </div>
          </Row>
        )}
        {p.notable.length > 0 && (
          <Row icon={<AlertCircleIcon className="h-4 w-4" />} label="Acts outside this computer">
            {p.notable.map((n, index) => (
              <span key={`${n.tool}-${index}`}>
                {index > 0 && ", "}
                <span className="text-[var(--fg)]">{n.title}</span>
                {fresh.notable.includes(n.tool) && <New />}
              </span>
            ))}
          </Row>
        )}
        {p.agents.length > 0 && (
          <Row icon={<TargetIcon className="h-4 w-4" />} label="Agent steps">
            <div className="flex flex-col gap-1">
              {p.agents.map((agent, index) => (
                <AgentLine key={`${agent.title}-${index}`} agent={agent} fresh={fresh.agents.includes(agent.title)} />
              ))}
            </div>
          </Row>
        )}
      </div>
    </section>
  );
}
