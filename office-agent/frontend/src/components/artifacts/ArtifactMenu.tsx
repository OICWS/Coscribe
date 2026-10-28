import { useEffect, useState } from "react";
import { deleteArtifact, duplicateArtifact, editedLabel, renameArtifact, type ArtifactSummary } from "../../lib/artifacts";
import { ConfirmDialog } from "../ConfirmDialog";
import { CopyIcon, ExternalLinkIcon, FolderIcon, LinkIcon, PencilIcon, TrashIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { PinIcon } from "./artifactIcons";
import { RenameDialog } from "./RenameDialog";

export interface ArtifactMenuProps {
  anchor: DOMRect;
  item: ArtifactSummary;
  pinned: boolean;
  onPin: () => void;
  /** Opens the file in its program, or shows it in the folder. */
  open: (reveal: boolean) => void;
  /** Entries only this kind of artifact has, between the file's own and Delete. */
  extra?: MenuEntry[];
  /** Where the viewing panel cannot follow the file (a detached window), renaming and deleting are left out. */
  fixedFile?: boolean;
  onChanged: (change: { kind: "renamed" | "duplicated" | "deleted"; item: ArtifactSummary }) => void;
  onClose: () => void;
}

const NOUN = { slides: "Presentation", docs: "Document", design: "Design", dashboard: "Dashboard" } as const;
const PROGRAM = { slides: "PowerPoint", docs: "Word", design: "browser", dashboard: "browser" } as const;

/** The menu every artifact has, from its card or from the name in its panel: what the file is,
 * open and show it, rename, copy, pin, delete (to the recycle bin). Kinds add their own entries. */
export function ArtifactMenu(props: ArtifactMenuProps) {
  const { item, onClose } = props;
  const [menuOpen, setMenuOpen] = useState(true);
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  useEffect(() => {
    if (!menuOpen && !dialog) onClose();
  }, [menuOpen, dialog, onClose]);

  const settle = (kind: "renamed" | "duplicated" | "deleted", next: ArtifactSummary) => {
    setDialog(null);
    props.onChanged({ kind, item: next });
  };
  const duplicate = () => {
    duplicateArtifact(item.id).then(
      (copy) => settle("duplicated", copy),
      (e: unknown) => setFailure(e instanceof Error ? e.message : String(e)),
    );
  };
  const remove = () => {
    deleteArtifact(item.id).then(
      () => settle("deleted", item),
      (e: unknown) => {
        setDialog(null);
        setFailure(e instanceof Error ? e.message : String(e));
      },
    );
  };
  const later = props.fixedFile ? { disabled: true, hint: "Main window" } : {};
  const entries: MenuEntry[] = [
    { note: `${NOUN[item.kind]} · ${editedLabel(item.modified_at, new Date()).replace("Edited", "Updated")}` },
    { label: `Open in ${PROGRAM[item.kind]}`, icon: <ExternalLinkIcon className="h-4 w-4" />, onSelect: () => props.open(false) },
    { label: "Show in folder", icon: <FolderIcon className="h-4 w-4" />, onSelect: () => props.open(true) },
    "divider",
    { label: "Rename", icon: <PencilIcon className="h-4 w-4" />, ...later, onSelect: () => setDialog("rename") },
    { label: "Duplicate", icon: <CopyIcon className="h-4 w-4" />, onSelect: duplicate },
    { label: props.pinned ? "Unpin" : "Pin", icon: <PinIcon className="h-4 w-4" />, accel: "p", hint: "P", onSelect: props.onPin },
    { label: "Copy path", icon: <LinkIcon className="h-4 w-4" />, onSelect: () => void navigator.clipboard?.writeText(item.location) },
    ...(props.extra?.length ? (["divider", ...props.extra] as MenuEntry[]) : []),
    "divider",
    { label: "Delete", icon: <TrashIcon className="h-4 w-4" />, danger: true, ...later, onSelect: () => setDialog("delete") },
  ];

  return (
    <>
      {menuOpen && <SlideMenu anchor={props.anchor} label={`Options for ${item.name}`} width={240} entries={entries} onClose={() => setMenuOpen(false)} />}
      {dialog === "rename" && <RenameDialog current={item.name} rename={(name) => renameArtifact(item.id, name)} onCancel={() => setDialog(null)} onDone={(next) => settle("renamed", next)} />}
      {dialog === "delete" && (
        <ConfirmDialog
          title={`Delete ${item.name}?`}
          description={`This moves ${item.name} to the Recycle Bin and removes it from Artifacts.`}
          onCancel={() => setDialog(null)}
          onConfirm={remove}
        />
      )}
      {failure && (
        <ConfirmDialog title="That did not work" description={failure} confirmLabel="OK" tone="neutral" onCancel={() => setFailure(null)} onConfirm={() => setFailure(null)} />
      )}
    </>
  );
}
