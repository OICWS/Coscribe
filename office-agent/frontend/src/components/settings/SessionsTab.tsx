import { ToggleSwitch } from "../ToggleSwitch";
import { isElectron } from "../../lib/electron";
import {
  ARCHIVE_INACTIVE_DAYS_KEY,
  ARCHIVE_INACTIVE_OPTIONS,
  BACKGROUND_AGENTS_KEY,
  FLASH_ON_ATTENTION_KEY,
  KEEP_AWAKE_KEY,
  KEEP_AWAKE_ON_BATTERY_KEY,
  PROMPT_SUGGESTIONS_KEY,
} from "./fields";
import { SettingRow, SettingRows, SettingsSection, fieldClass } from "./SettingRow";

interface SessionsTabProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

export function SessionsTab({ values, onChange }: SessionsTabProps) {
  const on = (key: string) => values[key] !== "false";
  const toggle = (key: string) => onChange(key, on(key) ? "false" : "true");
  const suggestions = on(PROMPT_SUGGESTIONS_KEY);
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
        <SettingRow
          label="Background agents"
          description="Let Coscribe hand work to sub-agents that run in the background while you keep chatting. They can use a lot of your usage."
          control={
            <ToggleSwitch
              label="Background agents"
              on={on(BACKGROUND_AGENTS_KEY)}
              onClick={() => toggle(BACKGROUND_AGENTS_KEY)}
            />
          }
        />
        <SettingRow
          label="Archive inactive conversations"
          description="Archive conversations after a period of no activity. A conversation that is open or has work running is never archived, and one you take out of the archive stays out."
          control={
            <select
              aria-label="Archive inactive conversations"
              className={`${fieldClass} w-40`}
              value={values[ARCHIVE_INACTIVE_DAYS_KEY] ?? ""}
              onChange={(e) => onChange(ARCHIVE_INACTIVE_DAYS_KEY, e.target.value)}
            >
              {ARCHIVE_INACTIVE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          }
        />
        {isElectron() && (
          <>
            <SettingRow
              label="Draw attention when Coscribe needs you"
              description="Flash the taskbar button when a reply finishes or Coscribe is waiting for you, and the window isn't in front."
              control={
                <ToggleSwitch
                  label="Draw attention when Coscribe needs you"
                  on={on(FLASH_ON_ATTENTION_KEY)}
                  onClick={() => toggle(FLASH_ON_ATTENTION_KEY)}
                />
              }
            />
            <SettingRow
              label="Keep computer awake while Coscribe works"
              description="Stop your computer from sleeping while a reply is being worked on, so long tasks can finish. The display can still turn off, and closing the laptop lid still sleeps it."
              control={
                <ToggleSwitch
                  label="Keep computer awake while Coscribe works"
                  on={on(KEEP_AWAKE_KEY)}
                  onClick={() => toggle(KEEP_AWAKE_KEY)}
                />
              }
            />
            {on(KEEP_AWAKE_KEY) && (
              <SettingRow
                label="Keep awake on battery power"
                control={
                  <ToggleSwitch
                    label="Keep awake on battery power"
                    on={on(KEEP_AWAKE_ON_BATTERY_KEY)}
                    onClick={() => toggle(KEEP_AWAKE_ON_BATTERY_KEY)}
                  />
                }
              />
            )}
          </>
        )}
      </SettingRows>
    </SettingsSection>
  );
}
