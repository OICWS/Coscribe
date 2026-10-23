import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  getSecrets,
  getSessionEnvironment,
  getThreadFolders,
  saveSessionEnvironment,
  saveThreadFolders,
  setThreadMeta,
} from "../lib/rest";
import { folderName, remember } from "../lib/recentFolders";
import type { SecretInfo } from "../types/settings";
import {
  EnvironmentRow,
  FoldersPage,
  SecretsPage,
  VariablesPage,
} from "./environment/EnvironmentPages";
import { toVariables, useScriptsDraft, type VariableRow } from "./environment/drafts";
import { ArrowLeftIcon, CloseIcon } from "./icons";
import { ScriptsPage } from "./environment/ScriptsPage";
import { primaryButtonClass, secondaryButtonClass } from "./settings/SettingRow";

type Page = "main" | "folders" | "scripts" | "secrets" | "variables";

const PAGE_TITLES: Record<Page, string> = {
  main: "Edit environment",
  folders: "Folders",
  scripts: "Scripts",
  secrets: "Secrets",
  variables: "Environment variables",
};

/** The open conversation's folders, which change over its socket so its page sees them. */
export interface OpenConversationFolders {
  folders: string[];
  onChange: (folders: string[]) => void;
}

/** Right-click a conversation > Edit environment: one row per part of what the conversation is
 * given, each opening its own page; Save changes keeps every page's edits at once. */
export function EnvironmentDialog({
  threadId,
  title,
  archived,
  openFolders,
  onArchiveChanged,
  onClose,
}: {
  threadId: string;
  title: string;
  archived: boolean;
  /** Set when this is the conversation on screen. */
  openFolders: OpenConversationFolders | null;
  onArchiveChanged: () => void;
  onClose: () => void;
}) {
  const [page, setPage] = useState<Page>("main");
  const [rows, setRows] = useState<VariableRow[] | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [secrets, setSecrets] = useState<SecretInfo[]>([]);
  const [folders, setFolders] = useState<string[]>([]);
  const [loadedFolders, setLoadedFolders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState("");
  // Read once: a change of the open conversation's folders while this is open must not undo edits here.
  const [initialOpenFolders] = useState(() => openFolders?.folders ?? null);
  const scripts = useScriptsDraft(threadId);

  const snapshot = (current: VariableRow[], picked: Set<string>, chosenFolders: string[]) =>
    JSON.stringify([current, [...picked].sort(), chosenFolders]);
  const dirty = rows !== null && (snapshot(rows, chosen, folders) !== loaded || scripts.dirty);

  useEffect(() => {
    let cancelled = false;
    const loadFolders = initialOpenFolders
      ? Promise.resolve({ folders: initialOpenFolders })
      : getThreadFolders(threadId);
    Promise.all([getSessionEnvironment(threadId), getSecrets(), loadFolders])
      .then(([environment, known, current]) => {
        if (cancelled) return;
        const loadedRows = Object.entries(environment.variables).map(([key, value]) => ({ key, value }));
        setRows(loadedRows);
        setChosen(new Set(environment.secrets));
        setFolders(current.folders);
        setLoadedFolders(current.folders);
        setLoaded(snapshot(loadedRows, new Set(environment.secrets), current.folders));
        setSecrets(known.secrets);
      })
      .catch(() => !cancelled && setError("Couldn't load this conversation's environment."));
    return () => {
      cancelled = true;
    };
  }, [threadId, initialOpenFolders]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const save = async () => {
    const variables = rows && toVariables(rows);
    if (!variables) return;
    if (typeof variables === "string") {
      setError(`${variables} appears twice.`);
      setPage("variables");
      return;
    }
    setSaving(true);
    setError(null);
    const result = await saveSessionEnvironment(threadId, { variables, secrets: [...chosen] });
    let failure = "error" in result ? result.error : await scripts.save();
    if (!failure && JSON.stringify(folders) !== JSON.stringify(loadedFolders)) {
      remember(folders);
      if (openFolders) openFolders.onChange(folders);
      else {
        const saved = await saveThreadFolders(threadId, folders);
        if ("error" in saved) failure = saved.error;
      }
    }
    setSaving(false);
    if (failure) setError(failure);
    else onClose();
  };

  const toggleArchive = async () => {
    const result = await setThreadMeta(threadId, { archived: !archived });
    if ("error" in result) {
      setError(result.error);
      return;
    }
    onArchiveChanged();
    onClose();
  };

  // A click beside the dialog closes it only when nothing is changed in it: a stray
  // click must not throw an edit away.
  const closeFromBackdrop = () => {
    if (!dirty) onClose();
  };

  const countOf = (n: number, noun: string) => (n === 0 ? "None" : `${n} ${noun}${n === 1 ? "" : "s"}`);
  const summaries: [Exclude<Page, "main">, string][] = [
    ["folders", folders.length === 0 ? "The default workspace" : folders.map(folderName).join(", ")],
    ["scripts", scripts.summary],
    ["secrets", chosen.size === 0 ? "None" : `${chosen.size} of ${secrets.length}`],
    ["variables", countOf(rows?.filter((row) => row.key.trim()).length ?? 0, "variable")],
  ];

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6" onClick={closeFromBackdrop}>
      <div
        role="dialog"
        aria-label="Edit environment"
        className="flex max-h-full w-full max-w-[36rem] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-2 px-6 pb-3 pt-5">
          {page !== "main" && (
            <button
              type="button"
              aria-label="Back"
              className="-ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={() => setPage("main")}
            >
              <ArrowLeftIcon className="h-4 w-4" />
            </button>
          )}
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-semibold leading-tight">{PAGE_TITLES[page]}</h2>
            {page === "main" && (
              <p className="mt-1 truncate text-sm text-[var(--muted)]">For this conversation: {title}</p>
            )}
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5 pt-1">
          {rows === null && !error && <p className="py-8 text-center text-sm text-[var(--muted)]">Loading...</p>}
          {rows !== null && page === "main" && (
            <div className="flex flex-col gap-3">
              {summaries.map(([target, value]) => (
                <EnvironmentRow key={target} title={PAGE_TITLES[target]} value={value} onOpen={() => setPage(target)} />
              ))}
            </div>
          )}
          {rows !== null && page === "folders" && <FoldersPage folders={folders} onChange={setFolders} />}
          {rows !== null && page === "scripts" && <ScriptsPage draft={scripts} />}
          {rows !== null && page === "secrets" && <SecretsPage secrets={secrets} chosen={chosen} onChange={setChosen} />}
          {rows !== null && page === "variables" && <VariablesPage rows={rows} onChange={setRows} />}
          {error && (
            <p role="alert" className="pt-4 text-sm text-[var(--danger)]">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-[var(--border)] px-6 py-4">
          <button
            type="button"
            className="mr-auto rounded-lg px-1 text-sm text-[var(--danger)] hover:underline"
            onClick={() => void toggleArchive()}
          >
            {archived ? "Unarchive conversation" : "Archive conversation"}
          </button>
          <button type="button" className={secondaryButtonClass} onClick={onClose}>
            Cancel
          </button>
          <button type="button" className={primaryButtonClass} disabled={rows === null || saving} onClick={() => void save()}>
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
