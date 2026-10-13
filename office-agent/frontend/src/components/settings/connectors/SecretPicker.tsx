import type { SecretInfo } from "../../../types/settings";
import { fieldClass } from "../SettingRow";

/** Puts `{{secret:NAME}}` into the text field it sits under, at the caret. */
export function SecretPicker({
  secrets,
  onPick,
}: {
  secrets: SecretInfo[];
  onPick: (placeholder: string) => void;
}) {
  if (secrets.length === 0) return null;
  return (
    <select
      aria-label="Insert a secret"
      className={`${fieldClass} h-8 w-fit text-[13px]`}
      value=""
      onChange={(e) => e.target.value && onPick(`{{secret:${e.target.value}}}`)}
    >
      <option value="">Insert a secret…</option>
      {secrets.map((secret) => (
        <option key={secret.name} value={secret.name}>
          {secret.name}
        </option>
      ))}
    </select>
  );
}
