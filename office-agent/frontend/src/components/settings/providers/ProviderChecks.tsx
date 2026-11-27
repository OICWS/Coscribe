import { useState } from "react";
import { testProvider } from "../../../lib/rest";
import { fieldClass, secondaryButtonClass } from "../SettingRow";
import { providerConnection } from "./catalog";
import type { ProviderForm } from "./ProviderPage";

type Check = "connection" | "tools";
type Result = { form: ProviderForm; model: string; text: string; error: boolean };

export function ProviderChecks({ form }: { form: ProviderForm }) {
  const [selected, setSelected] = useState("");
  const [running, setRunning] = useState<Check | null>(null);
  const [results, setResults] = useState<Partial<Record<Check, Result>>>({});
  const model = form.models.includes(selected) ? selected : form.defaultModel;
  const shown = Object.entries(results).filter(([, result]) => result?.form === form && result.model === model);

  const run = async (check: Check) => {
    const toolCalling = check === "tools";
    setRunning(check);
    setResults((previous) => ({ ...previous, [check]: undefined }));
    const show = (text: string, error: boolean) => setResults((previous) => ({
      ...previous,
      [check]: { form, model, text, error },
    }));
    try {
      const { error } = await testProvider(providerConnection(form), model, toolCalling);
      const passed = toolCalling ? "Tool call and result verified." : "Streaming reply verified.";
      show(error ?? passed, Boolean(error));
    } catch {
      show("Couldn't run the provider test.", true);
    } finally {
      setRunning(null);
    }
  };

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-[17px] font-medium">Test model</h3>
      <div className="flex flex-wrap items-center gap-2">
        {form.models.length > 1 && (
          <select aria-label="Model to test" className={fieldClass} value={model} onChange={(e) => setSelected(e.target.value)}>
            {form.models.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        )}
        <button type="button" className={secondaryButtonClass} disabled={!model || running !== null} onClick={() => void run("connection")}>
          {running === "connection" ? "Testing connection..." : "Test connection"}
        </button>
        <button type="button" className={secondaryButtonClass} disabled={!model || running !== null} onClick={() => void run("tools")}>
          {running === "tools" ? "Testing tool calling..." : "Test tool calling"}
        </button>
      </div>
      {shown.map(([check, result]) => (
        <p key={check} role="status" className={`text-[13px] ${result?.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>{result?.text}</p>
      ))}
    </section>
  );
}
