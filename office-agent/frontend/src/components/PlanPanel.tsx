import { lazy, Suspense, useRef, useState } from "react";
import { quoteOf, type PlanComment } from "../lib/planComments";
import type { ProgressItem } from "../lib/workflowProgress";
import { useDockPanel } from "./dock/dockContext";
import { MessageCircleIcon } from "./icons";
import { CommentBox, CommentList } from "./PlanComments";
import { TaskList } from "./TaskList";

const Markdown = lazy(() => import("./Markdown").then((m) => ({ default: m.Markdown })));

/** The plan in a panel of its own, like Browser: the plan the model last
 * proposed, rendered, and the task list it is working through. Selected
 * words can be commented on; the comments go to the model with Revise. */
export function PlanPanel({
  tasks,
  plan,
  busy,
  comments,
  onComments,
}: {
  tasks: ProgressItem[];
  plan: string | null;
  busy: boolean;
  comments: PlanComment[];
  onComments: (comments: PlanComment[]) => void;
}) {
  const dock = useDockPanel();
  const host = useRef<HTMLDivElement>(null);
  const doc = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<{ quote: string; top: number } | null>(null);

  // Selected words open the comment box under them; a click that selects nothing closes it.
  const onSelected = () => {
    const selection = window.getSelection();
    const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    const quote = range && !selection?.isCollapsed && doc.current?.contains(range.commonAncestorContainer) ? quoteOf(selection!.toString()) : "";
    if (!quote || !range || !host.current) return setDraft(null);
    const box = host.current.getBoundingClientRect();
    setDraft({ quote, top: range.getBoundingClientRect().bottom - box.top + host.current.scrollTop + 8 });
  };
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <span className="min-w-0 flex-1 truncate px-1 text-[15px]">Plan</span>
        {dock.controls}
      </div>
      <div ref={host} className="relative min-h-0 flex-1 overflow-y-auto px-5 pb-6 pt-2">
        {plan !== null && (
          <section className="mb-6">
            <p className="mb-3 flex items-center gap-1.5 text-[13px] text-[var(--muted)]">
              <MessageCircleIcon className="h-3.5 w-3.5" />
              Select any text to leave a comment for Claude
            </p>
            <Suspense fallback={<p className="whitespace-pre-wrap text-sm">{plan}</p>}>
              <div ref={doc} className="plan-doc" onMouseUp={onSelected} onKeyUp={onSelected}>
                <Markdown text={plan} />
              </div>
            </Suspense>
          </section>
        )}
        {draft && (
          <CommentBox
            top={draft.top}
            onCancel={() => setDraft(null)}
            onAdd={(text) => {
              onComments([...comments, { id: crypto.randomUUID(), quote: draft.quote, text }]);
              window.getSelection()?.removeAllRanges();
              setDraft(null);
            }}
          />
        )}
        {tasks.length > 0 && (
          <section>
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Tasks</h2>
            <TaskList tasks={tasks} strike live={busy} />
          </section>
        )}
        {comments.length > 0 && <CommentList comments={comments} onRemove={(id) => onComments(comments.filter((c) => c.id !== id))} />}
        {plan === null && tasks.length === 0 && <p className="text-sm text-[var(--muted)]">No plan in this conversation yet.</p>}
      </div>
    </div>
  );
}
