import { describeArgs, describeResult, rawJson, type FieldLine } from "../../lib/toolFields";

function Lines({ lines }: { lines: FieldLine[] }) {
  return (
    <>
      {lines.map((line, index) => (
        <div key={index} className="leading-relaxed">
          <div className="flex items-baseline gap-1.5">
            {line.name !== null && <span className="shrink-0 font-mono text-xs text-[var(--muted)]">{line.name}:</span>}
            {line.value !== null && <span className="min-w-0 whitespace-pre-wrap break-words">{line.value}</span>}
          </div>
          {line.children.length > 0 && (
            <div className="ml-3 border-l border-[var(--border)] pl-2.5">
              <Lines lines={line.children} />
            </div>
          )}
        </div>
      ))}
    </>
  );
}

/** A call's arguments as "name: value" lines; nothing when there are none. */
export function ArgLines({ args, pad = true }: { args: Record<string, unknown>; pad?: boolean }) {
  const lines = describeArgs(args);
  if (lines.length === 0) return null;
  return (
    <div className={`max-h-48 overflow-y-auto text-sm ${pad ? "px-3 py-2" : ""}`}>
      <Lines lines={lines} />
    </div>
  );
}

/** A result as plain text, in a box of bounded height. */
export function ResultText({ result, pad = true }: { result: unknown; pad?: boolean }) {
  const view = describeResult(result);
  return (
    <div className={`max-h-60 overflow-y-auto text-sm ${pad ? "px-3 py-2" : ""}`}>
      {view.kind === "lines" ? <Lines lines={view.lines} /> : <p className="whitespace-pre-wrap break-words">{view.text}</p>}
    </div>
  );
}

/** The original arguments and result as JSON, folded away. */
export function RawFold({ args, result, pad = true }: { args: Record<string, unknown>; result?: unknown; pad?: boolean }) {
  return (
    <details className={`${pad ? "px-3 pb-2" : "mt-1"} text-xs text-[var(--muted)]`}>
      <summary className="cursor-pointer select-none hover:text-[var(--fg)]">Raw</summary>
      <pre className="mt-1 max-h-60 overflow-auto whitespace-pre-wrap break-all font-mono">
        {rawJson(result === undefined ? { arguments: args } : { arguments: args, result })}
      </pre>
    </details>
  );
}
