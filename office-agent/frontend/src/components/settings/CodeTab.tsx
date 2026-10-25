import { useEffect } from "react";
import { useCodePermissions } from "../../lib/useCodePermissions";
import type { useCodeStatus } from "../../lib/useCodeStatus";
import { useConfiguredModels } from "../../lib/useConfiguredModels";
import { CodeDownload } from "../CodeModuleStatus";
import { ToggleSwitch } from "../ToggleSwitch";
import { CODE_MODEL_KEY, CODE_MODULE_ENABLED_KEY } from "./fields";
import { SelectMenu } from "./SelectMenu";
import { SettingRow, SettingRows, SettingsSection } from "./SettingRow";

interface CodeTabProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  code: ReturnType<typeof useCodeStatus>;
  codexFolder?: string;
}

function CodeModelSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const models = useConfiguredModels();
  const options = value && !models.includes(value) ? [value, ...models] : models;
  return (
    <SelectMenu
      ariaLabel="Model for code"
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

/** Codex, which both the command sandbox and the code module run on, then the code module: what
 * a chat hands programming tasks to when allowed. How it may act follows the permission mode, as
 * a chat's tools do. */
export function CodeTab({ values, onChange, code, codexFolder }: CodeTabProps) {
  const approvals = useCodePermissions();
  const model = values[CODE_MODEL_KEY] ?? "";
  const { refresh } = code;
  // Settings save a moment after a change; re-check the model after that.
  useEffect(() => {
    const timer = window.setTimeout(refresh, 1200);
    return () => window.clearTimeout(timer);
  }, [model, refresh]);
  const problem = code.status?.model_problem;
  return (
    <div className="flex flex-col gap-10">
      <SettingsSection
        title="Codex"
        description="OpenAI's coding agent, downloaded once. The command sandbox and the code module both run on it. coscribe uses the one version it was tested with and checks the download; when an update moves to a newer one, Update replaces the old."
      >
        <div className="py-3.5">
          <CodeDownload code={code} folder={codexFolder} />
        </div>
      </SettingsSection>

      <SettingsSection
        title="Code module"
        description="Writes and runs code in your folder: scripts that process your files, tools you'll reuse, fixes for a script that fails."
      >
        <SettingRows>
          <SettingRow
            label="Chats can hand tasks to Code"
            description="A chat passes work that needs real code -- processing data across files, a script to reuse -- to the code module and gets its report back. You approve its commands either way."
            control={
              <ToggleSwitch
                label="Chats can hand tasks to Code"
                on={values[CODE_MODULE_ENABLED_KEY] === "true"}
                onClick={() => onChange(CODE_MODULE_ENABLED_KEY, values[CODE_MODULE_ENABLED_KEY] === "true" ? "false" : "true")}
              />
            }
          />
          <SettingRow
            label="Model for code"
            description={
              <>
                What Codex runs on for these tasks. Left as the chat's model, it works when the chat uses an OpenAI model
                or a provider that serves the Responses API (DeepSeek does); with Claude or Gemini in the chat, pick one
                here.
                {problem && <span className="mt-1 block text-[var(--danger)]">{problem}</span>}
              </>
            }
            control={<CodeModelSelect value={model} onChange={(v) => onChange(CODE_MODEL_KEY, v)} />}
          />
        </SettingRows>
      </SettingsSection>

      {approvals.permissions && (
        <SettingsSection
          title="Approvals"
          description="Codex can't run commands: nothing would keep them inside your folder, so only plain reads of the folder run. It asks before each file change, under the permission mode. Allowing here skips the question for good, except in Plan mode. An Approve card can also allow it for one task only."
        >
          <SettingRows>
            <SettingRow
              label="Change files without asking"
              description="Edits Codex makes with its own patch tool. Accept-edits mode already allows these."
              control={
                <ToggleSwitch
                  label="Change files without asking"
                  on={approvals.permissions.apply_code_change === "allow"}
                  onClick={() =>
                    approvals.set("apply_code_change", approvals.permissions?.apply_code_change === "allow" ? "ask" : "allow")
                  }
                />
              }
            />
          </SettingRows>
          {approvals.error && <p className="mt-2 text-sm text-[var(--danger)]">{approvals.error}</p>}
        </SettingsSection>
      )}
    </div>
  );
}
