import { useEffect, useState } from "react";
import { editedLabel, type SystemItem } from "../../lib/artifacts";
import { duplicateSystem, removeSystem, renameSystem } from "../../lib/designSystemItems";
import { ConfirmDialog } from "../ConfirmDialog";
import { CopyIcon, PencilIcon, TrashIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { PinIcon } from "./artifactIcons";
import { RenameDialog } from "./RenameDialog";

/** The menu of a design system on the Artifacts page: it is a record of the library, so there is
 * no file to open or show, and Delete is for good. */
export function DesignSystemMenu({
  anchor,
  item,
  pinned,
  onPin,
  onChanged,
  onClose,
}: {
  anchor: DOMRect;
  item: SystemItem;
  pinned: boolean;
  onPin: () => void;
  onChanged: () => void;
  onClose: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(true);
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  useEffect(() => {
    if (!menuOpen && !dialog) onClose();
  }, [menuOpen, dialog, onClose]);

  const run = (job: Promise<void>) =>
    job.then(
      () => {
        setDialog(null);
        onChanged();
      },
      (e: unknown) => {
        setDialog(null);
        setFailure(e instanceof Error ? e.message : String(e));
      },
    );
  const entries: MenuEntry[] = [
    { note: `Design system · ${editedLabel(item.modified_at, new Date()).replace("Edited", "Updated")}` },
    { label: "Rename", icon: <PencilIcon className="h-4 w-4" />, onSelect: () => setDialog("rename") },
    { label: "Duplicate", icon: <CopyIcon className="h-4 w-4" />, onSelect: () => void run(duplicateSystem(item.id)) },
    { label: pinned ? "Unpin" : "Pin", icon: <PinIcon className="h-4 w-4" />, accel: "p", hint: "P", onSelect: onPin },
    "divider",
    { label: "Delete", icon: <TrashIcon className="h-4 w-4" />, danger: true, onSelect: () => setDialog("delete") },
  ];
  return (
    <>
      {menuOpen && <SlideMenu anchor={anchor} label={`Options for ${item.name}`} width={240} entries={entries} onClose={() => setMenuOpen(false)} />}
      {dialog === "rename" && (
        <RenameDialog
          current={item.name}
          rename={(name) => renameSystem(item.id, name)}
          onCancel={() => setDialog(null)}
          onDone={() => {
            setDialog(null);
            onChanged();
          }}
        />
      )}
      {dialog === "delete" && (
        <ConfirmDialog
          title={`Delete ${item.name}?`}
          description="This deletes the design system for good. Decks already made from it keep their own copy."
          onCancel={() => setDialog(null)}
          onConfirm={() => void run(removeSystem(item.id))}
        />
      )}
      {failure && (
        <ConfirmDialog title="That did not work" description={failure} confirmLabel="OK" tone="neutral" onCancel={() => setFailure(null)} onConfirm={() => setFailure(null)} />
      )}
    </>
  );
}
