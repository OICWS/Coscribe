import { useRef, useState } from "react";
import { uploadSkill } from "../../../lib/rest";
import { ArrowLeftIcon, UploadIcon } from "../../icons";

/** Settings > Skills > Add > Upload skill (no security-scan UI: we don't
 * scan). Top-level, not nested in SkillsTab. */
export function UploadSkillView({ onBack, onUploaded }: { onBack: () => void; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const save = async () => {
    if (!file) return;
    setSaving(true);
    setError(null);
    const result = await uploadSkill(file);
    setSaving(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    onUploaded();
  };

  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        className="flex w-fit items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--fg)]"
        onClick={onBack}
      >
        <ArrowLeftIcon className="h-3.5 w-3.5" /> Your skills
      </button>
      <div>
        <h2 className="text-lg font-semibold">Upload skill</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Add a skill to your workspace.</p>
      </div>
      <div>
        <div className="mb-1.5 text-sm font-medium">Skill file</div>
        <div
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-10 text-center ${
            dragging ? "border-[var(--accent)] bg-[var(--card-bg)]" : "border-[var(--border)]"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const dropped = e.dataTransfer.files[0];
            if (dropped) setFile(dropped);
          }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <UploadIcon className="h-5 w-5 text-[var(--muted)]" />
          {file ? (
            <span className="text-sm font-medium">{file.name}</span>
          ) : (
            <span className="text-sm text-[var(--muted)]">Drag and drop a skill file here, or browse</span>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".md,.zip,.skill"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <ul className="mt-2 list-disc pl-5 text-xs text-[var(--muted)]">
          <li>.md file must contain skill name and description formatted in YAML</li>
          <li>.zip or .skill file must include a SKILL.md file</li>
        </ul>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={!file || saving}
          className="rounded-md bg-[var(--accent)] px-4 py-1.5 text-sm font-medium text-[var(--accent-fg)] disabled:opacity-40"
          onClick={save}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button type="button" className="rounded-md border border-[var(--border)] px-4 py-1.5 text-sm" onClick={onBack}>
          Cancel
        </button>
        {error && <span className="text-sm text-red-500">{error}</span>}
        {!file && !error && <span className="text-sm text-[var(--muted)]">Choose a file to continue.</span>}
      </div>
    </div>
  );
}
