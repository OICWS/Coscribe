import { useState } from "react";
import { DirBrowserModal } from "./DirBrowserModal";
import { CloseIcon, FolderIcon } from "../icons";
import { SelectMenu } from "./SelectMenu";
import { SettingRow, SettingRowInput, SettingRows, SettingsSection, fieldClass, secondaryButtonClass } from "./SettingRow";
import { SKILLS_DIR_KEY, WORKSPACE_FIELDS, WORKSPACE_ROOT_KEY, type DirEntry, type DirPermission } from "./fields";

interface WorkspaceTabProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  dirEntries: DirEntry[];
  onDirEntriesChange: (entries: DirEntry[]) => void;
}

const DIR_PERMISSION_OPTIONS = [
  { value: "read", label: "Read only" },
  { value: "read-write", label: "Read and write" },
  { value: "read-write-delete", label: "Read, write and delete" },
] as const;

export function WorkspaceTab({ values, onChange, dirEntries, onDirEntriesChange }: WorkspaceTabProps) {
  const [addValue, setAddValue] = useState("");
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserTarget, setBrowserTarget] = useState<"root" | "skills" | "extra">("extra");

  const setPermission = (path: string, permission: DirPermission) => {
    onDirEntriesChange(dirEntries.map((e) => (e.path === path ? { ...e, permission } : e)));
  };

  const removeEntry = (path: string) => {
    onDirEntriesChange(dirEntries.filter((e) => e.path !== path));
  };

  const addPaths = (raw: string) => {
    const paths = raw
      .split(",")
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
    if (paths.length === 0) return;
    const existing = new Set(dirEntries.map((e) => e.path));
    const additions = paths.filter((p) => !existing.has(p)).map((path) => ({ path, permission: "read" as const }));
    if (additions.length > 0) onDirEntriesChange([...dirEntries, ...additions]);
    setAddValue("");
  };

  const browse = (target: "root" | "skills" | "extra") => {
    setBrowserTarget(target);
    setBrowserOpen(true);
  };
  const pathRow = (key: string, label: string, description: string, placeholder: string, target?: "root" | "skills") => (
    <SettingRow
      key={key}
      label={label}
      description={description}
      control={
        <div className="flex items-center gap-2">
          <SettingRowInput value={values[key] ?? ""} placeholder={placeholder} onChange={(v) => onChange(key, v)} />
          {target && (
            <button type="button" className={secondaryButtonClass} onClick={() => browse(target)}>
              Browse…
            </button>
          )}
        </div>
      }
    />
  );
  const field = (key: string) => WORKSPACE_FIELDS.find((f) => f.key === key)!;
  const fieldRow = (key: string, target?: "skills") =>
    pathRow(key, field(key).label, field(key).description, field(key).placeholder, target);

  return (
    <div className="flex flex-col gap-10">
      <SettingsSection title="Folders">
        <SettingRows>
          {pathRow(
            WORKSPACE_ROOT_KEY,
            "Default workspace",
            "Where a conversation works when you don't pick a folder for it.",
            "./workspace",
            "root",
          )}
          {fieldRow(SKILLS_DIR_KEY, "skills")}
        </SettingRows>
      </SettingsSection>

      <SettingsSection
        title="Other folders"
        description="Coscribe can always read and change the workspace. Give it more folders here. Only folders set to read, write and delete let it delete, move or rename files; deleted files go to the Recycle Bin. On Windows, scripts read nothing outside these folders, so add a folder as read only for a script to read it."
      >
        {dirEntries.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--muted)]">No other folders yet.</p>
        ) : (
          <div className="mt-3 flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
            {dirEntries.map((entry) => (
              <div key={entry.path} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <FolderIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
                <span className="min-w-0 flex-1 truncate">{entry.path}</span>
                <SelectMenu
                  ariaLabel={`Access to ${entry.path}`}
                  value={entry.permission}
                  options={DIR_PERMISSION_OPTIONS}
                  onChange={(v) => setPermission(entry.path, v)}
                />
                <button
                  type="button"
                  aria-label={`Remove ${entry.path}`}
                  className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-red-500"
                  onClick={() => removeEntry(entry.path)}
                >
                  <CloseIcon className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="mt-3 flex gap-2">
          <input
            aria-label="Folder to add"
            className={`${fieldClass} min-w-0 flex-1`}
            placeholder="Paste a folder path, or several separated by commas"
            value={addValue}
            onChange={(e) => setAddValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") addPaths(addValue);
            }}
          />
          <button type="button" className={secondaryButtonClass} disabled={!addValue.trim()} onClick={() => addPaths(addValue)}>
            Add
          </button>
          <button type="button" className={secondaryButtonClass} onClick={() => browse("extra")}>
            Browse…
          </button>
        </div>
      </SettingsSection>

      <SettingsSection title="Files">
        <SettingRows>{fieldRow("COSCRIBE_MEMORY_PATH")}</SettingRows>
      </SettingsSection>

      <SettingsSection title="Advanced">
        <SettingRows>
          {fieldRow("COSCRIBE_MCP_CONFIG_PATH")}
          {fieldRow("COSCRIBE_PROVIDERS_CONFIG_PATH")}
          {fieldRow("COSCRIBE_HOOKS_CONFIG_PATH")}
        </SettingRows>
      </SettingsSection>

      {browserOpen && (
        <DirBrowserModal
          onClose={() => setBrowserOpen(false)}
          onSelect={(path) => {
            if (browserTarget === "root") {
              onChange(WORKSPACE_ROOT_KEY, path);
            } else if (browserTarget === "skills") {
              onChange(SKILLS_DIR_KEY, path);
            } else {
              addPaths(path);
            }
            setBrowserOpen(false);
          }}
        />
      )}
    </div>
  );
}
