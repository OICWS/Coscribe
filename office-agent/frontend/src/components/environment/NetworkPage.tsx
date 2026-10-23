import type { NetworkAccess } from "../../types/settings";
import { fieldClass } from "../settings/SettingRow";
import type { NetworkDraft } from "./drafts";

const OPTIONS: { mode: NetworkAccess["mode"]; title: string; detail: string }[] = [
  {
    mode: "none",
    title: "None",
    detail: "No web search, web pages, downloads or browser steps. Scripts have no network.",
  },
  {
    mode: "limited",
    title: "Limited",
    detail:
      "The assistant opens, downloads from and uses in the browser only the domains below. Searching still works. Scripts have no network.",
  },
  {
    mode: "full",
    title: "Full",
    detail: "Any site, and scripts can reach the internet too.",
  },
];

export function NetworkPage({ draft }: { draft: NetworkDraft }) {
  return (
    <section className="flex flex-col gap-3">
      <p className="text-[13px] leading-relaxed text-[var(--muted)]">
        How far this conversation may reach the internet. Connectors are set in Settings &gt; Connectors. A script that
        runs without isolation is not held to this.
      </p>
      <div role="radiogroup" aria-label="Network access" className="flex flex-col gap-2">
        {OPTIONS.map((option) => (
          <label
            key={option.mode}
            className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 hover:bg-[var(--card-bg)] ${
              draft.mode === option.mode ? "border-[var(--accent)]" : "border-[var(--border)]"
            }`}
          >
            <input
              type="radio"
              name="network-mode"
              className="mt-1 h-4 w-4 shrink-0 accent-[var(--accent)]"
              checked={draft.mode === option.mode}
              onChange={() => draft.setMode(option.mode)}
            />
            <span className="flex flex-col gap-1">
              <span className="text-[15px] font-medium">{option.title}</span>
              <span className="text-[13px] leading-relaxed text-[var(--muted)]">{option.detail}</span>
            </span>
          </label>
        ))}
      </div>
      {draft.mode === "limited" && (
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Allowed domains</span>
          <textarea
            aria-label="Allowed domains"
            className={`${fieldClass} min-h-28 font-mono text-[13px]`}
            value={draft.domains}
            spellCheck={false}
            placeholder="example.com"
            onChange={(e) => draft.setDomains(e.target.value)}
          />
          <span className="text-xs text-[var(--muted)]">
            One per line. A domain covers its subdomains. * allows every site.
          </span>
        </label>
      )}
    </section>
  );
}
