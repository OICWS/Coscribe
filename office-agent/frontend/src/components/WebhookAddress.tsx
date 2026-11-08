import { useEffect, useState } from "react";
import { getTaskWebhook, newWebhookKey, waitForWebhookSample } from "../lib/rest";
import type { WebhookInfo } from "../types/settings";
import type { WorkflowInput } from "../types/workflow";
import { ConfirmDialog } from "./ConfirmDialog";
import { CopyButton } from "./CopyButton";

// Where a program on this computer sends a "webhook" task its events, and with what key (decision
// 0040): shown on the task page and in its form, with a PowerShell line to paste and a way to keep
// the next event as a sample to map inputs from.

const SAMPLE_POLL_MS = 2000;
const copy = "rounded p-1 text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
const button = "rounded-md border border-[var(--border)] px-2.5 py-1 text-[13px] hover:bg-[var(--card-bg)]";

/** A body to try the task with: the sample when there is one, else one value per input. */
function exampleBody(info: WebhookInfo, inputs: WorkflowInput[]): string {
  if (info.sample !== null && info.sample !== undefined) {
    const sample = JSON.stringify(info.sample);
    if (sample.length <= 200) return sample;
  }
  const values = inputs.map((input) => [input.name, input.type === "number" ? 1 : "..."]);
  return JSON.stringify(Object.fromEntries(values.length ? values : [["text", "..."]]));
}

function powerShell(info: WebhookInfo, body: string, key: string): string {
  return (
    `Invoke-RestMethod -Method Post -Uri "${info.url}" ` +
    `-Headers @{ Authorization = "Bearer ${key}" } ` +
    `-ContentType "application/json" -Body '${body.replace(/'/g, "''")}'`
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="contents">
      <span className="pt-1 text-[13px] text-[var(--muted)]">{label}</span>
      <div className="flex min-w-0 items-center gap-1">{children}</div>
    </div>
  );
}

const HIDDEN = "•".repeat(24);

function KeyRow({
  info,
  shown,
  onShow,
  onNewKey,
}: {
  info: WebhookInfo;
  shown: boolean;
  onShow: (shown: boolean) => void;
  onNewKey: () => void;
}) {
  const [replacing, setReplacing] = useState(false);
  const link = "text-[13px] text-[var(--muted)] hover:underline";
  return (
    <Row label="Key">
      {info.key === null ? (
        <span className="text-[13px] text-[var(--danger)]">The key was lost from the keychain.</span>
      ) : (
        <>
          <code className="truncate font-mono text-[12.5px]" data-testid="webhook-key">
            {shown ? info.key : HIDDEN}
          </code>
          <CopyButton getText={() => info.key ?? ""} title="Copy the key" className={copy} />
          <button type="button" className={link} onClick={() => onShow(!shown)}>
            {shown ? "Hide" : "Show"}
          </button>
        </>
      )}
      <button type="button" className={`ml-2 ${link}`} onClick={() => setReplacing(true)}>
        New key
      </button>
      {replacing && (
        <ConfirmDialog
          title="Make a new key?"
          description="Programs that send with the old key will be refused until they use the new one."
          confirmLabel="Make a new key"
          onCancel={() => setReplacing(false)}
          onConfirm={() => {
            setReplacing(false);
            onNewKey();
          }}
        />
      )}
    </Row>
  );
}

function SampleRow({ info, onToggle }: { info: WebhookInfo; onToggle: () => void }) {
  const fields = Object.keys(info.fields ?? {}).length;
  return (
    <div className="flex flex-wrap items-center gap-2 text-[13px]">
      <button type="button" className={button} onClick={onToggle} data-testid="webhook-sample">
        {info.waiting ? "Stop waiting" : "Wait for a sample"}
      </button>
      <span className="text-[var(--muted)]">
        {info.waiting
          ? "Waiting: the next event is kept here without starting a run."
          : fields > 0
            ? `Sample kept: ${fields} ${fields === 1 ? "field" : "fields"} to fill inputs from.`
            : "Keep the next event as a sample, to pick which of its fields fill the inputs."}
      </span>
    </div>
  );
}

export function WebhookAddress({
  taskId,
  inputs,
  onInfo,
}: {
  taskId: string;
  inputs: WorkflowInput[];
  /** Each time what the task has changes: a new sample's fields fill the form's choices. */
  onInfo?: (info: WebhookInfo) => void;
}) {
  const [info, setInfo] = useState<WebhookInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Hidden until asked, in the example too, so a shared screen or screenshot doesn't give it away.
  const [shown, setShown] = useState(false);
  const take = (next: WebhookInfo) => {
    setInfo(next);
    onInfo?.(next);
  };
  useEffect(() => {
    getTaskWebhook(taskId)
      .then(take)
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per task
  }, [taskId]);
  const waiting = info?.waiting ?? false;
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(() => {
      getTaskWebhook(taskId)
        .then(take)
        .catch(() => undefined);
    }, SAMPLE_POLL_MS);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- polls while it waits
  }, [taskId, waiting]);
  if (error) return <p className="text-[13px] text-[var(--danger)]">Its address couldn't be read: {error}</p>;
  if (!info) return null;
  const body = exampleBody(info, inputs);
  const example = powerShell(info, body, info.key ?? HIDDEN);
  return (
    <div className="flex flex-col gap-2 rounded-md border border-[var(--border)] p-3" data-testid="webhook-address">
      {!info.listening && info.error && <p className="text-[13px] text-[var(--danger)]">{info.error}</p>}
      <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-x-2 gap-y-1.5">
        <Row label="Address">
          <code className="truncate font-mono text-[12.5px]" data-testid="webhook-url">
            {info.url}
          </code>
          <CopyButton getText={() => info.url} title="Copy the address" className={copy} />
        </Row>
        <KeyRow info={info} shown={shown} onShow={setShown} onNewKey={() => void newWebhookKey(taskId).then(take)} />
      </div>
      <details className="text-[13px]">
        <summary className="cursor-pointer text-[var(--muted)] hover:text-[var(--fg)]">Try it from PowerShell</summary>
        <div className="mt-1.5 flex items-start gap-1">
          <pre className="min-w-0 flex-1 overflow-x-auto rounded-md bg-[var(--card-bg)] p-2 font-mono text-[12px] whitespace-pre-wrap break-all">
            {shown ? example : powerShell(info, body, HIDDEN)}
          </pre>
          <CopyButton getText={() => example} title="Copy the command" className={copy} />
        </div>
      </details>
      <SampleRow info={info} onToggle={() => void waitForWebhookSample(taskId, !waiting).then(take)} />
      <p className="text-xs text-[var(--muted)]">
        Only programs on this computer can send to it, with the key in an Authorization header; web pages can't.
      </p>
    </div>
  );
}
