import { useState } from "react";
import { testProvider } from "../../../lib/rest";
import { fieldClass, secondaryButtonClass } from "../SettingRow";
import { providerConnection } from "./catalog";
import type { ProviderForm } from "./ProviderPage";

type Result = { form: ProviderForm; model: string; text: string; error: boolean };

/** One test: the agent needs tool calling, so a reply alone would pass a model that can't work. */
export function ProviderChecks({ form }: { form: ProviderForm }) {
  const [selected, setSelected] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const model = form.models.includes(selected) ? selected : form.defaultModel;
  const shown = result?.form === form && result.model === model ? result : null;

  const run = async () => {
    setRunning(true);
    setResult(null);
    try {
      const { error } = await testProvider(providerConnection(form), model);
      setResult({ form, model, text: error ?? "The model replied and used a tool. It's ready to use.", error: Boolean(error) });
    } catch {
      setResult({ form, model, text: "Couldn't run the test.", error: true });
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-[17px] font-medium">Test model</h3>
      <p className="text-[13px] text-[var(--muted)]">Sends a short request, including one tool call, to check that the model works with Coscribe.</p>
      <div className="flex flex-wrap items-center gap-2">
        {form.models.length > 1 && (
          <select aria-label="Model to test" className={fieldClass} value={model} onChange={(e) => setSelected(e.target.value)}>
            {form.models.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        )}
        <button type="button" className={secondaryButtonClass} disabled={!model || running} onClick={() => void run()}>
          {running ? "Testing..." : "Test"}
        </button>
      </div>
      {shown && (
        <p role="status" className={`text-[13px] ${shown.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>{shown.text}</p>
      )}
    </section>
  );
}
