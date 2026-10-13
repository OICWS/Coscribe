import { useContext, useState } from "react";
import { blockedWriteOf, groupHasPendingApproval, isRunning, summarizeGroupParts, summarizeItemParts, type ToolRunGroup } from "../../lib/transcriptGrouping";
import { type LogItem } from "../../state/reducer";
import { type PptxShapeCapture } from "../PptxShapeOverlay";
import { BlockedFolderCard } from "../BlockedFolderCard";
import { type ToolOrApprovalItem } from "./types";
import { pptxOverlayTargetOf, inSentence } from "./helpers";
import { ConnectorTools } from "./contexts";
import { SummaryLabel, Disclosure } from "./SummaryLabel";
import { ToolPreview } from "./ToolPreview";
import { ApprovalPreview } from "./ApprovalPreview";

/** A run of tool calls: one sentence-like summary with a chevron after
 * it; opened, a bordered list with a row per call, each opening to its
 * result. A run holding an unresolved approval is shown unwrapped
 * instead -- an action waiting on the user must never sit behind a
 * disclosure. `group.id` is stable across that change, so the open state
 * survives the approval resolving. */
export function ToolRunGroupView({
  group,
  live,
  onApprove,
  onPptxShapePicked,
}: {
  group: ToolRunGroup;
  live: boolean;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const [open, setOpen] = useState(false);
  // Which calls are opened, held here rather than in each row: a row is unmounted
  // when a newer call arrives (one call has no list, several do) or an approval
  // takes the group over, and would otherwise come back closed.
  const [openCalls, setOpenCalls] = useState<ReadonlySet<string>>(new Set());
  const toggleCall = (id: string) =>
    setOpenCalls((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  const connectorTools = useContext(ConnectorTools);

  if (groupHasPendingApproval(group)) {
    return (
      <div className="flex max-w-full flex-col gap-1.5 self-start">
        {group.items.map((item) => (
          <ToolCallRow key={item.id} item={item} onApprove={onApprove} onPptxShapePicked={onPptxShapePicked} />
        ))}
      </div>
    );
  }

  const header = summarizeGroupParts(group.items, live, connectorTools);
  const single = group.items.length === 1 ? group.items[0] : null;
  return (
    <div className="w-full max-w-[92%] self-start text-sm">
      <button
        type="button"
        aria-expanded={open}
        className="inline-flex max-w-full items-center gap-1 text-left text-[var(--muted)] hover:text-[var(--fg)]"
        onClick={() => {
          // A lone call's detail is its group's body; it stays open when more calls join.
          if (single) toggleCall(single.id);
          setOpen((v) => !v);
        }}
      >
        <span className="min-w-0">
          {header.shown.map((parts, index) => (
            <span key={index}>
              {index > 0 && ", "}
              <SummaryLabel parts={inSentence(parts, index)} />
            </span>
          ))}
          {header.more > 0 &&
            `${header.shown.length > 0 ? ", and " : "And "}${header.more} more action${header.more === 1 ? "" : "s"}`}
          {header.active && (
            <>
              {header.shown.length > 0 && ", "}
              <SummaryLabel parts={inSentence(header.active, header.shown.length)} />
            </>
          )}
        </span>
        <Disclosure open={open} />
      </button>
      {single && <ToolPreview item={single} onPptxShapePicked={onPptxShapePicked} />}
      {group.items.map((item) => {
        const blocked = blockedWriteOf(item);
        return blocked ? <BlockedFolderCard key={item.id} blocked={blocked} /> : null;
      })}
      {open && (
        <div className="mt-2 overflow-hidden rounded-xl border border-[var(--border)]">
          {single ? (
            <ToolDetail item={single} onApprove={onApprove} onPptxShapePicked={onPptxShapePicked} />
          ) : (
            group.items.map((item, index) => (
              <ToolStepRow
                key={item.id}
                item={item}
                running={isRunning(item, live)}
                first={index === 0}
                open={openCalls.has(item.id)}
                onToggle={() => toggleCall(item.id)}
                onApprove={onApprove}
                onPptxShapePicked={onPptxShapePicked}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

/** One call inside an opened run. */
function ToolStepRow({
  item,
  running,
  first,
  open,
  onToggle,
  onApprove,
  onPptxShapePicked,
}: {
  item: ToolOrApprovalItem;
  running: boolean;
  first: boolean;
  open: boolean;
  onToggle: () => void;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  return (
    <div className={first ? "" : "border-t border-[var(--border)]"}>
      <button
        type="button"
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-[var(--card-bg)]"
        onClick={onToggle}
      >
        <span className="min-w-0 flex-1 truncate">
          <SummaryLabel parts={summarizeItemParts(item, running)} />
        </span>
        <span className="text-[var(--muted)]">
          <Disclosure open={open} />
        </span>
      </button>
      <div className="px-3">
        <ToolPreview item={item} onPptxShapePicked={onPptxShapePicked} />
      </div>
      {open && (
        <div className="border-t border-[var(--border)]">
          <ToolDetail item={item} onApprove={onApprove} onPptxShapePicked={onPptxShapePicked} />
        </div>
      )}
    </div>
  );
}

/** What an opened call shows: its result, or for an approval, what was
 * asked and decided. */
function ToolDetail({
  item,
  onApprove,
  onPptxShapePicked,
}: {
  item: ToolOrApprovalItem;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  if (item.kind === "approval") {
    return (
      <div className="px-3 py-2">
        <ApprovalDetail item={item} onApprove={onApprove} onPptxShapePicked={onPptxShapePicked} />
      </div>
    );
  }
  if (item.toolName === "run_code_command") return <CodeCommandDetail item={item} />;
  if (item.result === undefined) {
    return <p className="px-3 py-2 text-[var(--muted)]">No result yet.</p>;
  }
  return (
    <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-all bg-[var(--bg)] px-3 py-2 font-mono text-xs leading-relaxed">
      {typeof item.result === "string" ? item.result : JSON.stringify(item.result, null, 2)}
    </pre>
  );
}

/** A code-module command opened: the command, then what it printed. */
function CodeCommandDetail({ item }: { item: Extract<ToolOrApprovalItem, { kind: "tool" }> }) {
  const script = typeof item.arguments.script === "string" ? item.arguments.script : "";
  const result = item.result;
  const record = result !== null && typeof result === "object" ? (result as Record<string, unknown>) : null;
  const output = record ? String(record.output ?? "") : result === undefined ? "" : String(result);
  const exitCode = record && typeof record.exit_code === "number" ? record.exit_code : null;
  return (
    <div className="flex flex-col font-mono text-xs leading-relaxed">
      <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all px-3 py-2">{script}</pre>
      {result === undefined ? (
        <p className="border-t border-[var(--border)] px-3 py-2 font-sans text-[var(--muted)]">No result yet.</p>
      ) : (
        <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-all border-t border-[var(--border)] bg-[var(--bg)] px-3 py-2">
          {output || "(no output)"}
          {exitCode ? `\n(exit code ${exitCode})` : ""}
        </pre>
      )}
    </div>
  );
}

/** A call waiting on the user's approval: a bordered card, open by
 * default, with the Approve/Deny controls. */
function ToolCallRow({
  item,
  onApprove,
  onPptxShapePicked,
}: {
  item: ToolOrApprovalItem;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const [open, setOpen] = useState(() => item.kind === "approval" && item.status === "pending");
  const isPendingApproval = item.kind === "approval" && item.status === "pending";

  return (
    <div
      className={`max-w-[92%] self-start rounded-xl border bg-[var(--card-bg)] px-3 py-2 text-sm ${
        isPendingApproval ? "border-[var(--accent)]" : "border-[var(--border)] hover:bg-[var(--panel-bg)]"
      }`}
    >
      <button
        type="button"
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 text-left text-[var(--fg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate">
          <SummaryLabel parts={summarizeItemParts(item)} />
        </span>
        <span className="text-[var(--muted)]">
          <Disclosure open={open} />
        </span>
      </button>
      <ToolPreview item={item} onPptxShapePicked={onPptxShapePicked} />
      {open && (
        <div className="mt-1.5">
          {item.kind === "tool" ? (
            item.result !== undefined && (
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap break-all">
                {typeof item.result === "string" ? item.result : JSON.stringify(item.result, null, 2)}
              </pre>
            )
          ) : (
            <ApprovalDetail item={item} onApprove={onApprove} onPptxShapePicked={onPptxShapePicked} />
          )}
        </div>
      )}
    </div>
  );
}

/** run_python_script/run_node_script/run_background_script are the tools
 * with no sandbox around them -- the script text IS the entire safety
 * review, so they get their own larger, clearly-labeled code block
 * instead of being buried, JSON-escaped, inside a generic arguments dump
 * the way every other tool's args are. run_background_script's arguments
 * carry the same script/description shape as the other two (see
 * tools/background_tasks.py), so it reuses this exact rendering. */
function ApprovalDetail({
  item,
  onApprove,
  onPptxShapePicked,
}: {
  item: Extract<LogItem, { kind: "approval" }>;
  onApprove: (id: string, approved: boolean, scope?: "task") => void;
  onPptxShapePicked: (capture: PptxShapeCapture) => void;
}) {
  const isScript =
    item.toolName === "run_python_script" ||
    item.toolName === "run_code_command" ||
    item.toolName === "run_node_script" ||
    item.toolName === "run_background_script" ||
    item.toolName === "run_background_command";
  const scriptArgs = item.arguments;
  const isShellCommand = item.toolName === "run_background_command";
  const scriptText = isShellCommand ? scriptArgs.command : scriptArgs.script;
  const hasPreview = Boolean(item.beforePreview || item.afterPreview);
  const pptxTarget = pptxOverlayTargetOf(item.arguments);
  // The code module's actions can be allowed for the rest of their task.
  const codeAction = item.toolName === "run_code_command" || item.toolName === "apply_code_change";
  return (
    <>
      {item.reviewerNote && item.status === "pending" && (
        <p className="mb-1.5 text-[13px] text-[var(--muted)]">{item.reviewerNote}</p>
      )}
      {hasPreview && (
        <ApprovalPreview
          beforePreview={item.beforePreview}
          afterPreview={item.afterPreview}
          pptxTarget={pptxTarget}
          onPptxShapePicked={onPptxShapePicked}
        />
      )}
      {isScript ? (
        <div className="flex flex-col gap-1.5">
          {typeof scriptArgs.description === "string" && scriptArgs.description && (
            <div className="text-xs text-[var(--muted)]">{scriptArgs.description}</div>
          )}
          <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-all rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 font-mono text-xs leading-normal">
            {typeof scriptText === "string" ? scriptText : JSON.stringify(scriptText)}
          </pre>
          <div className="text-xs text-[var(--muted)]">
            {item.toolName === "run_code_command"
              ? "The code module runs this with this app's own access and no sandbox: it can read and change any file this app can and use the network. Review it before approving."
              : isShellCommand
                ? "This command runs through your shell with this app's own access and no sandbox: it can read and change any file this app can and use the network. Unlike a script, nothing limits where it writes. Review it before approving."
                : "This script isn’t sandboxed: it can read any file this app can and use the network. It can write only in the workspace and folders you added -- a safeguard against mistakes, not a security boundary. Review it before approving."}
          </div>
        </div>
      ) : (
        Object.keys(item.arguments).length > 0 && (
          <pre className="max-h-32 overflow-y-auto whitespace-pre-wrap break-all text-xs text-[var(--muted)]">{JSON.stringify(item.arguments, null, 2)}</pre>
        )
      )}
      {item.status === "pending" ? (
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            className="rounded-md bg-[var(--accent)] px-3 py-1 text-sm text-[var(--accent-fg)]"
            onClick={() => onApprove(item.id, true)}
          >
            Approve
          </button>
          {codeAction && (
            <button
              type="button"
              className="rounded-md border border-[var(--border)] px-3 py-1 text-sm"
              onClick={() => onApprove(item.id, true, "task")}
            >
              Allow for this task
            </button>
          )}
          <button
            type="button"
            className="rounded-md border border-[var(--border)] px-3 py-1 text-sm"
            onClick={() => onApprove(item.id, false)}
          >
            Deny
          </button>
        </div>
      ) : (
        <>
          <div className="mt-1 text-xs text-[var(--muted)]">{item.status === "approved" ? "Approved" : "Denied"}</div>
          {item.result !== undefined && (
            <pre className="mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap break-all text-xs text-[var(--muted)]">
              {typeof item.result === "string" ? item.result : JSON.stringify(item.result, null, 2)}
            </pre>
          )}
        </>
      )}
    </>
  );
}
