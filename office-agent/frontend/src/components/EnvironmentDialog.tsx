import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { folderName } from "../lib/folderName";
import { createEnvironment, deleteEnvironment, getConfig, getEnvironments, getSecrets, updateEnvironment } from "../lib/rest";
import { ALLOWED_FOLDERS_CHANGED, buildDirEntries, type DirEntry } from "./settings/fields";
import type { Environment, EnvironmentFields, SecretInfo } from "../types/settings";
import { ConfirmDialog } from "./ConfirmDialog";
import { EnvironmentRow, VariablesPage } from "./environment/EnvironmentPages";
import { FoldersSection, SecretsSection, SitesSection } from "./environment/WorkspaceSections";
import {
  runSummary,
  useMachineLimits,
  useNetworkDraft,
  type MachineLimits,
  type RunSwitches,
} from "./environment/drafts";
import { formatEnvText, parseEnvText } from "./environment/envText";
import { ArrowLeftIcon, CloseIcon } from "./icons";
import { ScriptsPage } from "./environment/ScriptsPage";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "./settings/SettingRow";

type Page = "main" | "folders" | "sites" | "secrets" | "scripts" | "variables";

const PAGE_TITLES: Record<Page, string> = {
  main: "Edit workspace",
  folders: "Allowed folders",
  sites: "Sites",
  secrets: "Secrets",
  scripts: "Scripts and commands",
  variables: "Environment variables",
};

function listSummary(names: string[], none: string): string {
  if (names.length === 0) return none;
  const shown = names.slice(0, 3).join(", ");
  return names.length > 3 ? `${shown} and ${names.length - 3} more` : shown;
}

export const DEFAULT_ENVIRONMENT = "default";

const BLANK: EnvironmentFields = {
  name: "",
  folders: [],
  network: { mode: "limited", domains: ["*"] },
  secrets: [],
  variables: {},
  scripts: true,
  commands: true,
  unisolated: false,
};

function plural(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? "" : "s"}`;
}

function usedBy(environment: Environment | null): string {
  if (environment === null) return "A new workspace";
  const tasks = environment.tasks > 0 ? ` and ${plural(environment.tasks, "scheduled task")}` : "";
  if (environment.id === DEFAULT_ENVIRONMENT) return `Used by every conversation that hasn't chosen another${tasks}`;
  return `Used by ${plural(environment.used_by, "conversation")}${tasks}`;
}

export function whereItsConversationsGo(environment: Environment): string {
  const users = [environment.used_by, environment.tasks].some((n) => n > 0);
  return users ? "Its conversations and scheduled tasks move to Default." : "Nothing uses it.";
}

interface EnvironmentDialogProps {
  /** The environment to edit; null makes a new one. */
  environmentId: string | null;
  onSaved: (environment: Environment) => void;
  onDeleted?: () => void;
  onClose: () => void;
}

/** One environment: where its conversations work and what they may reach, one page per part.
 * Save keeps every page's edits at once. */
export function EnvironmentDialog(props: EnvironmentDialogProps) {
  const [loaded, setLoaded] = useState<{ environment: Environment | null; secrets: SecretInfo[]; library: DirEntry[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { environmentId, onClose } = props;

  useEffect(() => {
    let cancelled = false;
    Promise.all([getEnvironments(), getSecrets(), getConfig()])
      .then(([{ environments }, known, config]) => {
        if (cancelled) return;
        const environment = environments.find((e) => e.id === environmentId) ?? null;
        if (environmentId !== null && environment === null) setError("This workspace no longer exists.");
        else setLoaded({ environment, secrets: known.secrets, library: buildDirEntries(config as unknown as Record<string, string | null>) });
      })
      .catch(() => !cancelled && setError("Couldn't load the workspace."));
    return () => {
      cancelled = true;
    };
  }, [environmentId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (loaded === null) {
    return createPortal(
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6" onClick={onClose}>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] px-6 py-8 text-sm text-[var(--muted)]">
          {error ?? "Loading..."}
        </div>
      </div>,
      document.body,
    );
  }
  return <EnvironmentEditor {...props} environment={loaded.environment} secrets={loaded.secrets} library={loaded.library} />;
}

/** Every page's edits, kept until Save. */
function useEnvironmentDraft(start: EnvironmentFields) {
  const [name, setName] = useState(start.name);
  const [folders, setFolders] = useState(start.folders);
  const [chosen, setChosen] = useState(new Set(start.secrets));
  const [variablesText, setVariablesText] = useState(() => formatEnvText(start.variables));
  const [run, setRun] = useState<RunSwitches>({
    scripts: start.scripts,
    commands: start.commands,
    unisolated: start.unisolated,
  });
  const network = useNetworkDraft(start.network);
  const snapshot = () => JSON.stringify([name, folders, network.current, [...chosen].sort(), variablesText, run]);
  const [initialSnapshot] = useState(snapshot);
  const fields = (variables: Record<string, string>): EnvironmentFields => ({
    name: name.trim(),
    folders,
    network: network.current,
    secrets: [...chosen],
    variables,
    ...run,
  });
  const dirty = snapshot() !== initialSnapshot;
  return { name, setName, folders, setFolders, chosen, setChosen, variablesText, setVariablesText, run, setRun, network, fields, dirty };
}

type EnvironmentDraft = ReturnType<typeof useEnvironmentDraft>;

function EditorHeader({
  page,
  environment,
  onBack,
  onClose,
}: {
  page: Page;
  environment: Environment | null;
  onBack: () => void;
  onClose: () => void;
}) {
  const iconButton =
    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]";
  return (
    <div className="flex items-start gap-2 px-6 pb-3 pt-5">
      {page !== "main" && (
        <button type="button" aria-label="Back" className={`-ml-2 ${iconButton}`} onClick={onBack}>
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
      )}
      <div className="min-w-0 flex-1">
        <h2 className="text-xl font-semibold leading-tight">
          {page === "main" && !environment ? "New workspace" : PAGE_TITLES[page]}
        </h2>
        {page === "main" && <p className="mt-1 truncate text-sm text-[var(--muted)]">{usedBy(environment)}</p>}
      </div>
      <button type="button" aria-label="Close" className={iconButton} onClick={onClose}>
        <CloseIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function MainPage({
  draft,
  library,
  limits,
  onOpen,
}: {
  draft: EnvironmentDraft;
  library: DirEntry[];
  limits: MachineLimits;
  onOpen: (page: Exclude<Page, "main">) => void;
}) {
  const parsed = parseEnvText(draft.variablesText);
  const variableCount = "variables" in parsed ? Object.keys(parsed.variables).length : 0;
  const access = new Map(library.map((entry) => [entry.path, entry.permission]));
  const more = draft.folders.slice(1).map((folder) => `${folderName(folder)}${access.get(folder) === "read" ? " (read only)" : ""}`);
  const { network } = draft;
  const sites = network.mode === "none" ? "None" : network.mode === "any" ? "Any site" : listSummary(network.sites, "None listed");
  const summaries: [Exclude<Page, "main">, string][] = [
    ["folders", listSummary(more, "None")],
    ["sites", sites],
    ["secrets", listSummary([...draft.chosen].sort(), "None")],
    ["scripts", runSummary(draft.run, limits)],
    ["variables", variableCount === 0 ? "None" : `${variableCount} variable${variableCount === 1 ? "" : "s"}`],
  ];
  return (
    <div className="flex flex-col gap-6">
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Name</span>
        <input
          aria-label="Workspace name"
          className={fieldClass}
          value={draft.name}
          maxLength={60}
          placeholder="e.g. Reports"
          onChange={(e) => draft.setName(e.target.value)}
        />
      </label>
      <FoldersSection part="main" folders={draft.folders} library={library} onChange={draft.setFolders} />
      <div className="flex flex-col gap-2">
        {summaries.map(([target, value]) => (
          <EnvironmentRow key={target} title={PAGE_TITLES[target]} value={value} onOpen={() => onOpen(target)} />
        ))}
      </div>
    </div>
  );
}

function EditorFooter({
  deletable,
  saving,
  creating,
  onDelete,
  onCancel,
  onSave,
}: {
  deletable: boolean;
  saving: boolean;
  creating: boolean;
  onDelete: () => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <div className="flex items-center gap-2 border-t border-[var(--border)] px-6 py-4">
      {deletable && (
        <button
          type="button"
          className="mr-auto rounded-lg px-1 text-sm text-[var(--danger)] hover:underline"
          onClick={onDelete}
        >
          Delete workspace
        </button>
      )}
      <button type="button" className={`${secondaryButtonClass} ${deletable ? "" : "ml-auto"}`} onClick={onCancel}>
        Cancel
      </button>
      <button type="button" className={primaryButtonClass} disabled={saving} onClick={onSave}>
        {saving ? "Saving…" : creating ? "Create" : "Save changes"}
      </button>
    </div>
  );
}

// One height on every page, the main page's, so moving between pages does not make the dialog jump;
// a longer page (many sites or folders) scrolls inside it.
const dialogClass =
  "flex h-[min(42rem,100%)] w-full max-w-[42.5rem] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-bg)] shadow-[var(--shadow)]";

function EnvironmentEditor({
  environment,
  secrets,
  library,
  onSaved,
  onDeleted,
  onClose,
}: EnvironmentDialogProps & { environment: Environment | null; secrets: SecretInfo[]; library: DirEntry[] }) {
  const [page, setPage] = useState<Page>("main");
  const draft = useEnvironmentDraft(environment ?? BLANK);
  const limits = useMachineLimits();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const deletable = environment !== null && environment.id !== DEFAULT_ENVIRONMENT;

  const save = async () => {
    const parsed = parseEnvText(draft.variablesText);
    if ("error" in parsed) {
      setError(parsed.error);
      setPage("variables");
      return;
    }
    const variables = parsed.variables;
    if (!draft.name.trim()) {
      setError("Give the workspace a name.");
      setPage("main");
      return;
    }
    setSaving(true);
    setError(null);
    const fields = draft.fields(variables);
    const result = environment ? await updateEnvironment(environment.id, fields) : await createEnvironment(fields);
    setSaving(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    // Saving can add folders to Allowed folders; an open Settings reloads them before it saves its own copy.
    window.dispatchEvent(new Event(ALLOWED_FOLDERS_CHANGED));
    onSaved(result);
    onClose();
  };

  const remove = async () => {
    if (!environment) return;
    const result = await deleteEnvironment(environment.id);
    setConfirmDelete(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    onDeleted?.();
    onClose();
  };

  // A click beside the dialog closes it only when nothing is changed in it: a stray click must
  // not throw an edit away.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6" onClick={() => !draft.dirty && onClose()}>
      <div
        role="dialog"
        aria-label={environment ? "Edit workspace" : "New workspace"}
        className={dialogClass}
        onClick={(e) => e.stopPropagation()}
      >
        <EditorHeader page={page} environment={environment} onBack={() => setPage("main")} onClose={onClose} />
        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-5 pt-1">
          {page === "main" && <MainPage draft={draft} library={library} limits={limits} onOpen={setPage} />}
          {page === "folders" && <FoldersSection part="more" folders={draft.folders} library={library} onChange={draft.setFolders} />}
          {page === "sites" && <SitesSection network={draft.network} secrets={secrets} chosen={draft.chosen} />}
          {page === "secrets" && <SecretsSection secrets={secrets} chosen={draft.chosen} onChange={draft.setChosen} />}
          {page === "scripts" && <ScriptsPage run={draft.run} limits={limits} onChange={draft.setRun} />}
          {page === "variables" && <VariablesPage text={draft.variablesText} onChange={draft.setVariablesText} />}
          {error && (
            <p role="alert" className="pt-4 text-sm text-[var(--danger)]">
              {error}
            </p>
          )}
        </div>
        <EditorFooter
          deletable={deletable}
          saving={saving}
          creating={environment === null}
          onDelete={() => setConfirmDelete(true)}
          onCancel={onClose}
          onSave={() => void save()}
        />
      </div>
      {confirmDelete && environment && (
        <ConfirmDialog
          title={`Delete ${environment.name}?`}
          description={whereItsConversationsGo(environment)}
          confirmLabel="Delete"
          onCancel={() => setConfirmDelete(false)}
          onConfirm={() => void remove()}
        />
      )}
    </div>,
    document.body,
  );
}
