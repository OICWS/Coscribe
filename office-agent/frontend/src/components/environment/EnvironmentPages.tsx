import { ChevronRightIcon } from "../icons";
import { fieldClass } from "../settings/SettingRow";

const introClass = "text-[13px] leading-relaxed text-[var(--muted)]";

/** One line of the dialog's first page: what a page holds, opened with a click. */
export function EnvironmentRow({ title, value, onOpen }: { title: string; value: string; onOpen: () => void }) {
  return (
    <button
      type="button"
      className="flex w-full items-center gap-3 rounded-lg border border-[var(--border)] px-3.5 py-2.5 text-left hover:bg-[var(--card-bg)]"
      onClick={onOpen}
    >
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-medium">{title}</span>
        <span className="truncate text-[13px] text-[var(--muted)]">{value}</span>
      </span>
      <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
    </button>
  );
}

const VARIABLES_PLACEHOLDER = `NODE_ENV=production
GIT_AUTHOR_NAME=Your Name

# Multiline values - wrap in quotes
CONFIG="key1=val1
key2=val2"`;

export function VariablesPage({ text, onChange }: { text: string; onChange: (text: string) => void }) {
  return (
    <section className="flex flex-col gap-3">
      <textarea
        aria-label="Environment variables"
        className={`${fieldClass} h-48 resize-y font-mono text-[13px] leading-relaxed`}
        value={text}
        placeholder={VARIABLES_PLACEHOLDER}
        spellCheck={false}
        autoCapitalize="off"
        autoCorrect="off"
        onChange={(e) => onChange(e.target.value)}
      />
      <p className={introClass}>
        One KEY=value per line, in .env format; # starts a comment and a quoted value may span lines. Plain text the
        assistant can read, such as a mode or a project name. For a key, use a secret. Scripts and the code module's
        commands get them as environment variables too, so a name such as PATH, PYTHONPATH, NODE_OPTIONS or a proxy
        variable changes how they run.
      </p>
    </section>
  );
}
