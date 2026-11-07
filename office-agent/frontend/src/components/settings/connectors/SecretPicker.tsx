import type { SecretInfo } from "../../../types/settings";
import { SelectMenu } from "../../SelectMenu";

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
    <SelectMenu
      ariaLabel="Insert a secret"
      variant="field"
      className="w-fit"
      value=""
      placeholder="Insert a secret…"
      options={secrets.map((secret) => ({ value: secret.name, label: secret.name }))}
      onChange={(name) => onPick(`{{secret:${name}}}`)}
    />
  );
}
