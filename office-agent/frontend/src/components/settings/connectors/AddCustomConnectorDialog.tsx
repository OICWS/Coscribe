import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getSecrets } from "../../../lib/rest";
import type { SecretInfo } from "../../../types/settings";
import { CloseIcon } from "../../icons";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { insertAtCaret, parseEnvLines, parseHeaderLines, secretProblems } from "./helpers";
import { SecretPicker } from "./SecretPicker";
import type { LocalServerArgs, RemoteServerArgs } from "./types";

/** Name plus an MCP server URL, or a local command for a server that runs
 * on this computer. */
export function AddCustomConnectorDialog({
  existing,
  onClose,
  onAdd,
}: {
  existing: string[];
  onClose: () => void;
  onAdd: (name: string, server: LocalServerArgs | RemoteServerArgs) => void;
}) {
  const [local, setLocal] = useState(false);
  const [name, setName] = useState("");
  const [serverUrl, setServerUrl] = useState("");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [env, setEnv] = useState("");
  const [headers, setHeaders] = useState("");
  const [secrets, setSecrets] = useState<SecretInfo[]>([]);
  const envRef = useRef<HTMLTextAreaElement>(null);
  const headersRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getSecrets()
      .then((res) => setSecrets(res.secrets))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const trimmedName = name.trim();
  const nameTaken = existing.includes(trimmedName);
  const urlOk = /^https?:\/\/\S+$/i.test(serverUrl.trim());
  const ready = trimmedName !== "" && !nameTaken && (local ? command.trim() !== "" : urlOk);
  let serverHost: string | null = null;
  try {
    serverHost = urlOk ? new URL(serverUrl.trim()).hostname : null;
  } catch {
    serverHost = null;
  }
  // A header goes to this server only, so its secrets must be allowed for the
  // host; an env value goes to the local command, which has no host.
  const problems = local ? secretProblems(env, secrets, null) : secretProblems(headers, secrets, serverHost);

  const submit = () => {
    if (!ready) return;
    onAdd(
      trimmedName,
      local
        ? { command: command.trim(), args: args.split(/\s+/).filter(Boolean), env: parseEnvLines(env) }
        : { server_url: serverUrl.trim(), ...(headers.trim() ? { headers: parseHeaderLines(headers) } : {}) },
    );
  };

  const hint = "mt-1.5 text-[13px] text-[var(--muted)]";
  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-connector-title"
        className="flex w-[min(640px,100vw-2rem)] flex-col gap-5 rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] p-7 shadow-[var(--shadow)]"
      >
        <div className="flex items-start gap-4">
          <h2 id="add-connector-title" className="flex-1 text-2xl font-semibold">
            Add custom connector
          </h2>
          <button
            type="button"
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>
        <p className="-mt-2 text-[15px] text-[var(--muted)]">Connect Coscribe to your data and tools.</p>

        <div>
          <input
            aria-label="Name"
            autoFocus
            className={`${fieldClass} h-10 w-full`}
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <p className={hint}>{nameTaken ? "A connector already has this name." : "Shown in the connectors list."}</p>
        </div>

        {local ? (
          <div className="flex flex-col gap-3">
            <input
              aria-label="Command"
              className={`${fieldClass} h-10 w-full font-mono text-[13px]`}
              placeholder="Command, e.g. npx"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
            />
            <input
              aria-label="Arguments"
              className={`${fieldClass} h-10 w-full font-mono text-[13px]`}
              placeholder="Arguments, separated by spaces"
              value={args}
              onChange={(e) => setArgs(e.target.value)}
            />
            <textarea
              ref={envRef}
              aria-label="Environment variables"
              className={`${fieldClass} h-auto min-h-20 w-full py-2 font-mono text-[13px]`}
              placeholder="Environment variables, one per line: KEY=value"
              value={env}
              onChange={(e) => setEnv(e.target.value)}
            />
            <SecretPicker secrets={secrets} onPick={(p) => setEnv(insertAtCaret(envRef.current, env, p))} />
            <p className="text-[13px] text-[var(--muted)]">It runs as a program on this computer, with your permissions.</p>
          </div>
        ) : (
          <div>
            <input
              aria-label="MCP server URL"
              className={`${fieldClass} h-10 w-full`}
              placeholder="MCP server URL"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <p className={hint}>
              The HTTPS address where the server accepts MCP requests, for example https://mcp.example.com/mcp.
            </p>
            <textarea
              ref={headersRef}
              aria-label="Headers"
              className={`${fieldClass} mt-3 h-auto min-h-16 w-full py-2 font-mono text-[13px]`}
              placeholder="Headers, one per line: Authorization: Bearer {{secret:NAME}}"
              value={headers}
              onChange={(e) => setHeaders(e.target.value)}
            />
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <SecretPicker
                secrets={secrets}
                onPick={(p) => setHeaders(insertAtCaret(headersRef.current, headers, p))}
              />
              <span className="text-[13px] text-[var(--muted)]">
                A secret from Settings &gt; Secrets is sent to this server only, so it must be allowed for its host.
              </span>
            </div>
          </div>
        )}
        {problems.length > 0 && (
          <p role="alert" className="-mt-2 text-sm text-[var(--danger)]">
            {problems.join(" ")}
          </p>
        )}
        <button
          type="button"
          className="-mt-2 w-fit text-sm text-[var(--accent)] hover:underline"
          onClick={() => setLocal((v) => !v)}
        >
          {local ? "Use a server URL instead" : "Run a local command instead"}
        </button>

        <p className="text-[15px] text-[var(--muted)]">
          Only use connectors from developers you trust. Coscribe can't check what their tools do or whether they
          change.
        </p>

        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButtonClass} onClick={onClose}>
            Cancel
          </button>
          <button type="button" className={primaryButtonClass} disabled={!ready} onClick={submit}>
            Continue
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
