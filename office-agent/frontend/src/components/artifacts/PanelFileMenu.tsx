import { useEffect, useState } from "react";
import { lookupArtifact, type ArtifactSummary } from "../../lib/artifacts";
import { openThreadFile } from "../../lib/rest";
import { ExternalLinkIcon, FolderIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { ArtifactMenu } from "./ArtifactMenu";
import { usePins } from "./usePins";

const PROGRAMS: Record<string, string> = { pptx: "PowerPoint", docx: "Word", xlsx: "Excel" };

/** The menu under the file's name in a viewing panel: the artifact menu when coscribe made the
 * file, else just what any file has (open it, show it). `extra` is what this kind of panel adds. */
export function PanelFileMenu({
  anchor,
  threadId,
  path,
  extra,
  onFileChanged,
  onClose,
}: {
  anchor: DOMRect;
  threadId: string;
  path: string;
  extra?: MenuEntry[];
  /** The panel's file was renamed (its new path) or deleted (null). Absent where the panel cannot follow. */
  onFileChanged?: (path: string | null) => void;
  onClose: () => void;
}) {
  const [artifact, setArtifact] = useState<ArtifactSummary | null | undefined>(undefined);
  const { pins, toggle } = usePins();
  useEffect(() => {
    lookupArtifact(threadId, path).then(setArtifact, () => setArtifact(null));
  }, [threadId, path]);
  const open = (reveal: boolean) => void openThreadFile(threadId, path, reveal);
  if (artifact === undefined) return null;
  if (artifact === null) {
    const program = PROGRAMS[path.split(".").pop()?.toLowerCase() ?? ""] ?? "the default app";
    const entries: MenuEntry[] = [
      { label: `Open in ${program}`, icon: <ExternalLinkIcon className="h-4 w-4" />, onSelect: () => open(false) },
      { label: "Show in folder", icon: <FolderIcon className="h-4 w-4" />, onSelect: () => open(true) },
      ...(extra?.length ? (["divider", ...extra] as MenuEntry[]) : []),
    ];
    return <SlideMenu anchor={anchor} label="File" width={240} entries={entries} onClose={onClose} />;
  }
  return (
    <ArtifactMenu
      anchor={anchor}
      item={artifact}
      pinned={pins.has(artifact.id)}
      onPin={() => toggle(artifact.id)}
      open={open}
      extra={extra}
      fixedFile={onFileChanged === undefined}
      onChanged={({ kind, item }) => {
        if (kind === "renamed") onFileChanged?.(item.path);
        if (kind === "deleted") onFileChanged?.(null);
      }}
      onClose={onClose}
    />
  );
}
