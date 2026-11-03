import { useRef, useState } from "react";
import { addDesignAsset, deleteDesignAsset, designAssetUrl, updateDesignAsset } from "../../lib/rest";
import type { DesignAsset } from "../../types/settings";
import { PlusIcon, TrashIcon } from "../icons";
import { fieldClass, secondaryButtonClass } from "./SettingRow";

const KINDS: [DesignAsset["kind"], string][] = [
  ["logo", "Logo"],
  ["icon", "Icon"],
  ["picture", "Picture"],
];
const ACCEPT = "image/svg+xml,image/png,image/jpeg,image/webp";

type AssetChange = Partial<Pick<DesignAsset, "name" | "kind" | "note">>;

/** A text field written when it is left, if it changed. */
function CommitField({
  label,
  value,
  placeholder,
  className,
  onCommit,
}: {
  label: string;
  value: string;
  placeholder?: string;
  className: string;
  onCommit: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  return (
    <input
      aria-label={label}
      className={className}
      placeholder={placeholder}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => draft.trim() !== value && onCommit(draft.trim())}
      onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
    />
  );
}

/** One kept picture: its thumbnail drawn by the server, its name, kind and note, and Remove. */
function AssetRow({ systemId, asset, onChange, onRemove }: { systemId: string; asset: DesignAsset; onChange: (fields: AssetChange) => void; onRemove: () => void }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-14 w-20 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[repeating-conic-gradient(var(--card-bg)_0_25%,transparent_0_50%)] bg-[length:12px_12px] p-1">
        <img src={designAssetUrl(systemId, asset.id)} alt={asset.name} className="max-h-full max-w-full object-contain" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex gap-2">
          <CommitField label="Picture name" value={asset.name} className={`${fieldClass} min-w-0 flex-1`} onCommit={(name) => onChange({ name })} />
          <select aria-label="Kind" className={`${fieldClass} w-28`} value={asset.kind} onChange={(e) => onChange({ kind: e.target.value as DesignAsset["kind"] })}>
            {KINDS.map(([kind, label]) => (
              <option key={kind} value={kind}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <CommitField
          label="When to use it"
          value={asset.note}
          placeholder="When to use it, e.g. on dark backgrounds"
          className={`${fieldClass} w-full`}
          onCommit={(note) => onChange({ note })}
        />
      </div>
      <span className="w-20 shrink-0 text-right text-xs text-[var(--muted)]">
        {asset.width && asset.height ? `${asset.width}×${asset.height}` : asset.file.split(".").pop()?.toUpperCase()}
      </span>
      <button type="button" aria-label={`Remove ${asset.name}`} title="Remove" className={`${secondaryButtonClass} !px-2.5`} onClick={onRemove}>
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

/** The system's logos, icons and pictures. Each is kept as soon as it is added or changed: a picture
 * is a file of its own, not part of what the form's Save sends. */
export function DesignSystemAssets({ systemId, initial }: { systemId: string; initial: DesignAsset[] }) {
  const [assets, setAssets] = useState(initial);
  const [problem, setProblem] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  const add = async (files: FileList | null) => {
    setProblem(null);
    for (const file of Array.from(files ?? [])) {
      const made = await addDesignAsset(systemId, file);
      if ("error" in made) {
        setProblem(`${file.name}: ${made.error}`);
        return;
      }
      setAssets((list) => [...list, made]);
    }
  };
  const change = async (asset: DesignAsset, fields: AssetChange) => {
    setProblem(null);
    const changed = await updateDesignAsset(systemId, asset.id, fields);
    if ("error" in changed) setProblem(changed.error);
    else setAssets((list) => list.map((a) => (a.id === asset.id ? changed : a)));
  };
  const remove = async (asset: DesignAsset) => {
    setProblem(null);
    const result = await deleteDesignAsset(systemId, asset.id);
    if ("error" in result) setProblem(result.error);
    else setAssets((list) => list.filter((a) => a.id !== asset.id));
  };

  return (
    <div className="flex max-w-3xl flex-col gap-3">
      {problem && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {problem}
        </p>
      )}
      {assets.map((asset) => (
        <AssetRow key={asset.id} systemId={systemId} asset={asset} onChange={(fields) => void change(asset, fields)} onRemove={() => void remove(asset)} />
      ))}
      <button
        type="button"
        className={`flex h-20 items-center justify-center gap-2 rounded-xl border border-dashed text-sm ${over ? "border-[var(--accent)] bg-[var(--card-bg)]" : "border-[var(--border)] text-[var(--muted)] hover:bg-[var(--card-bg)]"}`}
        onClick={() => picker.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          void add(e.dataTransfer.files);
        }}
      >
        <PlusIcon className="h-4 w-4" /> Add a logo or picture (SVG, PNG, JPEG or WebP, up to 2 MB)
      </button>
      <input
        ref={picker}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        data-testid="asset-file"
        onChange={(e) => {
          void add(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
