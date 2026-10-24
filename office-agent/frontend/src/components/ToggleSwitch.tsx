/** Shared boolean toggle -- used for scheduled tasks' enabled state
 * (RunPanel) and skill enable/disable (SkillsTab), replacing raw
 * checkboxes/text buttons with one consistent affordance. */
export function ToggleSwitch({
  on,
  onClick,
  label,
  disabled,
}: {
  on: boolean;
  onClick: () => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50 ${on ? "bg-[var(--accent)]" : "bg-[var(--border)]"}`}
    >
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-[var(--bg)] transition-[left] ${on ? "left-[18px]" : "left-0.5"}`}
      />
    </button>
  );
}
