import {
  lazy,
  Suspense,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
  type SVGProps,
} from "react";
import { askSideQuestion, type SideChatMessage } from "../lib/rest";
import { useDockPanel } from "./dock/dockContext";
import { ArrowUpIcon, EyeIcon } from "./icons";

const Markdown = lazy(() =>
  import("./Markdown").then((m) => ({ default: m.Markdown })),
);

/** A temporary conversation beside the current one. Its messages live only in this component:
 * closing the panel, another conversation or a reload drops them, because the answers were read
 * against the conversation as it was then. */
export function SideChatPanel({ threadId }: { threadId: string }) {
  const dock = useDockPanel();
  const [messages, setMessages] = useState<SideChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    box.current?.focus();
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight });
  }, [messages, waiting, error]);

  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [draft]);

  const send = async () => {
    const text = draft.trim();
    if (!text || waiting) return;
    const asked: SideChatMessage[] = [...messages, { role: "user", text }];
    setDraft("");
    setError(null);
    setMessages(asked);
    setWaiting(true);
    const result = await askSideQuestion(threadId, asked);
    if (!alive.current) return;
    setWaiting(false);
    if ("error" in result) setError(result.error);
    else setMessages([...asked, { role: "assistant", text: result.text }]);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className="flex h-12 shrink-0 items-center gap-2 px-3"
        {...dock.headerProps}
      >
        <span className="min-w-0 flex-1 truncate px-1 text-[15px]">
          Side chat
        </span>
        {dock.controls}
      </div>
      <p className="mx-3 mb-1 flex items-center gap-1.5 rounded-lg bg-[var(--card-bg)] px-3 py-2 text-[12.5px] text-[var(--muted)]">
        <EyeIcon className="h-3.5 w-3.5 shrink-0" />
        Coscribe sees this session. Nothing here is added to it.
      </p>
      <SideLog
        logRef={log}
        messages={messages}
        waiting={waiting}
        error={error}
      />
      <SideComposer
        boxRef={box}
        draft={draft}
        setDraft={setDraft}
        canSend={Boolean(draft.trim()) && !waiting}
        onSend={() => void send()}
      />
    </div>
  );
}

function SideLog({
  logRef,
  messages,
  waiting,
  error,
}: {
  logRef: RefObject<HTMLDivElement | null>;
  messages: SideChatMessage[];
  waiting: boolean;
  error: string | null;
}) {
  return (
    <div ref={logRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
      {messages.length === 0 ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
          <MessagesIcon className="h-6 w-6 text-[var(--muted)]" />
          <p className="text-[15px]">Ask about this conversation</p>
          <p className="text-[13px] text-[var(--muted)]">
            Answers come only from what the conversation holds, without opening
            files or using tools. You can ask while Coscribe is working.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 text-[14.5px]">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div
                key={i}
                className="ml-auto max-w-[88%] whitespace-pre-wrap rounded-2xl bg-[var(--user-bubble)] px-3.5 py-2 text-[var(--user-bubble-fg)]"
              >
                {m.text}
              </div>
            ) : (
              <div key={i} className="py-0.5 text-[var(--agent-bubble-fg)]">
                <Suspense
                  fallback={<p className="whitespace-pre-wrap">{m.text}</p>}
                >
                  <Markdown text={m.text} />
                </Suspense>
              </div>
            ),
          )}
          {waiting && (
            <p className="text-[13px] text-[var(--muted)] motion-safe:animate-pulse">
              Thinking…
            </p>
          )}
          {error && (
            <p role="alert" className="text-[13px] text-[var(--danger)]">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SideComposer({
  boxRef,
  draft,
  setDraft,
  canSend,
  onSend,
}: {
  boxRef: RefObject<HTMLTextAreaElement | null>;
  draft: string;
  setDraft: (text: string) => void;
  canSend: boolean;
  onSend: () => void;
}) {
  return (
    <div className="px-3 pb-3">
      <div className="flex items-end gap-2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] py-2 pl-3.5 pr-2 hover:border-[var(--border-hover)] focus-within:border-[var(--border-hover)]">
        <textarea
          ref={boxRef}
          rows={1}
          value={draft}
          aria-label="Side question"
          className="max-h-40 min-w-0 flex-1 resize-none self-center bg-transparent py-1 text-[14.5px] leading-6 outline-none"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing)
              return;
            e.preventDefault();
            onSend();
          }}
        />
        <button
          type="button"
          title="Send"
          disabled={!canSend}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)] text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-30"
          onClick={onSend}
        >
          <ArrowUpIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/** Two speech bubbles: Side chat, a conversation beside the current one. */
export function MessagesIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M16.5 10a6.5 6.5 0 0 1-9.4 5.8L3 17l1.2-3.8A6.5 6.5 0 1 1 16.5 10z" />
      <path d="M18.8 9.9a5.5 5.5 0 0 1 1.6 7.9l.9 3.2-3.2-.9a5.5 5.5 0 0 1-7.3-2.5" />
    </svg>
  );
}
