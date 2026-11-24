import { useState } from "react";
import { addPluginSource } from "../../../lib/rest";

/** Adds a GitHub repository with a marketplace.json to Discover. */
export function AddSourceForm({ onAdded }: { onAdded: () => void }) {
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const addSource = async () => {
    setBusy(true);
    setSourceError(null);
    const result = await addPluginSource(address);
    setBusy(false);
    if ("error" in result) return setSourceError(result.error);
    setAddress("");
    onAdded();
  };

  return (
    <section className="flex flex-col gap-2 border-t border-[var(--border)] pt-4">
      <label htmlFor="plugin-source" className="text-sm font-medium">
        Add a source
      </label>
      <p className="text-xs text-[var(--muted)]">
        A GitHub repository with a marketplace.json, as Claude and Codex plugin marketplaces have, such as a company's own.
      </p>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void addSource();
        }}
      >
        <input
          id="plugin-source"
          className="h-9 min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm outline-none focus:border-[var(--focus)]"
          placeholder="owner/repository or https://github.com/owner/repository"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        <button
          type="submit"
          disabled={busy || !address.trim()}
          className="shrink-0 rounded-lg bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-60"
        >
          {busy ? "Reading..." : "Add"}
        </button>
      </form>
      {sourceError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {sourceError}
        </p>
      )}
    </section>
  );
}
