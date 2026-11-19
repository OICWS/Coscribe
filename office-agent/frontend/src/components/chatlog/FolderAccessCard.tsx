import { useContext, useState } from "react";
import type { FolderAccessItem } from "../../state/folderAccess";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { FolderActionsContext } from "../folderActions";
import { CheckIcon, FolderIcon, PencilIcon, SettingsIcon } from "../icons";
import { SelectMenu } from "../SelectMenu";

type Access = "read" | "read-write" | "read-write-delete";

const FOLDER_ACCESS_OPTIONS = [
  { value: "read", label: "Read only" },
  { value: "read-write", label: "Read and write" },
  { value: "read-write-delete", label: "Read, write and delete" },
] as const;

function folderName(path: string): string {
  const parts = path.split(/[\\/]+/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

function accessLabel(access: string): string {
  return FOLDER_ACCESS_OPTIONS.find((o) => o.value === access)?.label.toLowerCase() ?? access;
}

/** What the person chose, as one line once the card is answered. */
function answeredLine(item: FolderAccessItem): { allowed: boolean; text: string } {
  const [choice, access] = (item.answer ?? "deny").split(":");
  const name = folderName(item.folder);
  if (choice === "allow") return { allowed: true, text: `Allowed ${name} · ${accessLabel(access)} · this workspace` };
  if (choice === "chat") return { allowed: true, text: `Allowed ${name} · ${accessLabel(access)} · this chat only` };
  if (choice === "workspace") return { allowed: false, text: `Saving in the workspace instead of ${name}` };
  return { allowed: false, text: item.reply ? `Not allowed ${name}: “${item.reply}”` : `Not allowed ${name}` };
}

/** The model asked for a folder outside the workspace (decision 0048). Allow adds it to Allowed
 * folders and to this conversation's workspace (decision 0053); Only this chat keeps it to this
 * conversation. */
export function FolderAccessCard({ item }: { item: FolderAccessItem }) {
  const actions = useContext(FolderActionsContext);
  const [access, setAccess] = useState<Access>(item.access === "write" ? "read-write" : "read");

  if (item.status === "answered") {
    const line = answeredLine(item);
    return (
      <div className="flex w-full items-center gap-2 rounded-xl border border-[var(--border)] px-3 py-2 text-sm" data-testid="folder-access-answered">
        {line.allowed ? (
          <CheckIcon className="h-4 w-4 shrink-0 text-[var(--success)]" />
        ) : (
          <FolderIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        )}
        <span className="min-w-0 flex-1 truncate" title={item.folder}>
          {line.text}
        </span>
      </div>
    );
  }

  const answer = (value: string) => actions?.onAnswerFolderAccess(item.id, value);
  const write = item.access === "write";
  return (
    <div
      className="flex w-full flex-col gap-3 rounded-xl border border-[var(--accent)] px-3.5 py-3 text-sm"
      data-waiting={item.id}
      data-testid="folder-access"
    >
      <div className="flex items-center gap-2.5">
        {write ? <PencilIcon className="h-4 w-4 shrink-0" /> : <FolderIcon className="h-4 w-4 shrink-0" />}
        <span className="min-w-0 flex-1 font-medium">
          {write ? "Save into a folder outside your workspace" : "Read a folder outside your workspace"}
        </span>
        <span className="flex shrink-0 items-center gap-1.5 text-[13px] font-medium text-[var(--warning)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--warning)]" />
          Waiting for you
        </span>
      </div>
      {item.reason && <p className="text-[13px] text-[var(--muted)]">{item.reason}</p>}
      <div className="flex items-center gap-2.5 rounded-lg border border-[var(--border)] px-2.5 py-2">
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-medium">{folderName(item.folder)}</span>
          <span className="truncate font-mono text-xs text-[var(--muted)]" title={item.folder}>
            {item.folder}
          </span>
        </div>
        <SelectMenu
          ariaLabel={`Access to ${folderName(item.folder)}`}
          variant="field"
          className="w-48 shrink-0"
          value={access}
          options={FOLDER_ACCESS_OPTIONS}
          onChange={setAccess}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={primaryButton} onClick={() => answer(`allow:${access}`)}>
          Allow
        </button>
        <button type="button" className={secondaryButton} onClick={() => answer(`chat:${access}`)}>
          Only this chat
        </button>
        {write && (
          <button type="button" className={secondaryButton} onClick={() => answer("workspace")}>
            Save in my workspace instead
          </button>
        )}
        <button
          type="button"
          className="h-8 rounded-md px-3 text-[13px] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
          onClick={() => answer("deny")}
        >
          Don’t allow
        </button>
        {actions?.onOpenFolderSettings && (
          <button
            type="button"
            className="ml-auto flex h-7 items-center gap-1.5 rounded-md px-2 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            onClick={actions.onOpenFolderSettings}
          >
            <SettingsIcon className="h-3.5 w-3.5" />
            Folder access
          </button>
        )}
      </div>
      <p className="text-xs text-[var(--muted)]">Allow adds it to this workspace and to Allowed folders, where other workspaces can pick it.</p>
    </div>
  );
}
