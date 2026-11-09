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
  SIDE_MODEL_KEY,
  WEBHOOK_PORT_KEY,
} from "./fields";
import { ConfiguredModelSelect } from "./ConfiguredModelSelect";
import { SelectMenu } from "../SelectMenu";
import { SettingRow, SettingRows, SettingsSection } from "./SettingRow";

interface SessionsTabProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

/** Where tasks that start on a program's events listen (decision 0040). */
function WebhookPortRow({ values, onChange }: SessionsTabProps) {
  return (
    <SettingRow
      label="Port for task events"
      description="A task that starts when a program sends it an event listens on this port, on this computer only. Change it if another program uses 8790, then restart Coscribe; programs then need the new address."
      control={
        <input
          aria-label="Port for task events"
          type="number"
          min={1024}
          max={65535}
          placeholder="8790"
          className="w-24 rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-sm outline-none"
          value={values[WEBHOOK_PORT_KEY] ?? ""}
          onChange={(e) => onChange(WEBHOOK_PORT_KEY, e.target.value)}
        />
      }
    />
  );
}

export function SessionsTab({ values, onChange }: SessionsTabProps) {
  const on = (key: string) => values[key] !== "false";
  const toggle = (key: string) => onChange(key, on(key) ? "false" : "true");
  const suggestions = on(PROMPT_SUGGESTIONS_KEY);
  return (
    <SettingsSection title="Sessions">
      <SettingRows>
        <SettingRow
          label="Model for side jobs"
          description="Runs the short calls around a chat: Auto mode's check of each risky action, conversation titles and prompt suggestions. Pick a cheaper model to spend less; if it can't be reached, the chat's model answers."
          control={
            <ConfiguredModelSelect
              ariaLabel="Model for side jobs"
              value={values[SIDE_MODEL_KEY] ?? ""}
              onChange={(v) => onChange(SIDE_MODEL_KEY, v)}
            />
          }
        />
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
            <SelectMenu
              ariaLabel="Archive inactive conversations"
              value={values[ARCHIVE_INACTIVE_DAYS_KEY] ?? ""}
              options={ARCHIVE_INACTIVE_OPTIONS}
              onChange={(v) => onChange(ARCHIVE_INACTIVE_DAYS_KEY, v)}
            />
          }
        />
        <WebhookPortRow values={values} onChange={onChange} />
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
