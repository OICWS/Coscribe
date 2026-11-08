import { useConfiguredModels } from "../../lib/useConfiguredModels";
import { SelectMenu } from "../SelectMenu";

/** A "provider:model" picked from the models already configured; "" is the chat's own model. A
 * saved value no longer configured stays listed, so opening Settings never changes it. */
export function ConfiguredModelSelect({
  ariaLabel,
  value,
  onChange,
}: {
  ariaLabel: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const models = useConfiguredModels();
  const options = value && !models.includes(value) ? [value, ...models] : models;
  return (
    <SelectMenu
      ariaLabel={ariaLabel}
      value={value}
      options={[
        { value: "", label: "Same as the chat's model" },
        ...options.map((model) => ({
          value: model,
          label: `${model.split(":").slice(1).join(":")} · ${model.split(":")[0]}`,
        })),
      ]}
      onChange={onChange}
    />
  );
}
