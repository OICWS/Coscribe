import { ToggleSwitch } from "../ToggleSwitch";
import { PROMPT_SUGGESTIONS_KEY } from "./fields";
import { SettingRow, SettingRows, SettingsSection } from "./SettingRow";

interface SessionsTabProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

export function SessionsTab({ values, onChange }: SessionsTabProps) {
  const suggestions = values[PROMPT_SUGGESTIONS_KEY] !== "false";
  return (
    <SettingsSection title="Sessions">
      <SettingRows>
        <SettingRow
          label="Prompt suggestions"
          description="Show a suggested next prompt in the message box after a reply: Enter sends it, Tab puts it in the box to edit. Suggestions add a little to your usage."
          control={
            <ToggleSwitch
              label="Prompt suggestions"
              on={suggestions}
              onClick={() => onChange(PROMPT_SUGGESTIONS_KEY, suggestions ? "false" : "true")}
            />
          }
        />
      </SettingRows>
    </SettingsSection>
  );
}
