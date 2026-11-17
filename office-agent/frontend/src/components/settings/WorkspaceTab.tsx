import { useState } from "react";
import { folderName } from "../../lib/recentFolders";
import { AllowedFoldersDialog } from "./AllowedFoldersDialog";
import { EnvironmentsSection } from "./EnvironmentsSection";
import { SettingRow, SettingRows, secondaryButtonClass } from "./SettingRow";
import type { DirEntry } from "./fields";

interface WorkspaceTabProps {
  dirEntries: DirEntry[];
  onDirEntriesChange: (entries: DirEntry[]) => void;
}

const SHORT_ACCESS = { read: "read", "read-write": "read and write", "read-write-delete": "read, write and delete" } as const;

function allowedSummary(entries: DirEntry[]): string {
  if (entries.length === 0) return "Folders every environment can use besides its own. None yet: when a chat needs another folder, it asks you first.";
  const shown = entries.slice(0, 3).map((entry) => `${folderName(entry.path)} (${SHORT_ACCESS[entry.permission]})`);
  const more = entries.length > 3 ? `, and ${entries.length - 3} more` : "";
  return `Folders every environment can use besides its own: ${shown.join(", ")}${more}. When a chat needs another one, it asks you first.`;
}

export function WorkspaceTab({ dirEntries, onDirEntriesChange }: WorkspaceTabProps) {
  const [managing, setManaging] = useState(false);
  return (
    <div className="flex flex-col gap-8">
      <EnvironmentsSection active />
      <SettingRows>
        <SettingRow
          label="Allowed folders"
          description={allowedSummary(dirEntries)}
          control={
            <button type="button" className={secondaryButtonClass} onClick={() => setManaging(true)}>
              Manage
            </button>
          }
        />
      </SettingRows>
      {managing && <AllowedFoldersDialog entries={dirEntries} onChange={onDirEntriesChange} onClose={() => setManaging(false)} />}
    </div>
  );
}
