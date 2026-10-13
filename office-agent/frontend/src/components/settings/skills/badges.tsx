import { SkillIcon } from "../../icons";

export function SkillBadge({ large }: { large?: boolean }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--card-bg)] text-[var(--muted)] ${
        large ? "h-14 w-14" : "h-11 w-11"
      }`}
    >
      <SkillIcon className={large ? "h-6 w-6" : "h-5 w-5"} />
    </div>
  );
}

export function CountBadge({ count }: { count: number }) {
  return (
    <span className="rounded-full bg-[var(--card-bg)] px-2 py-0.5 text-xs tabular-nums text-[var(--muted)]">{count}</span>
  );
}
