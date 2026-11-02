import { useEffect, useId, useState } from "react";
import { compiledGraph } from "../../lib/rest";
import type { Workflow } from "../../types/workflow";

// The workflow as LangGraph compiles it, every internal node included (a loop's next-item and
// keep-this-pass nodes), for seeing what actually runs. Mermaid is large, so it loads only here.

type Shown = { svg: string } | { error: string } | null;

async function draw(id: string, source: string): Promise<string> {
  const { default: mermaid } = await import("mermaid");
  const dark = document.documentElement.dataset.theme === "dark";
  mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "neutral", securityLevel: "strict" });
  const { svg } = await mermaid.render(id, source);
  return svg;
}

export function CompiledGraph({ workflow }: { workflow: Workflow }) {
  const id = `graph-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const [shown, setShown] = useState<Shown>(null);
  useEffect(() => {
    let live = true;
    void (async () => {
      const graph = await compiledGraph(workflow);
      if ("error" in graph) {
        if (live) setShown({ error: graph.error });
        return;
      }
      if (!graph.mermaid) {
        if (live) setShown({ error: "No steps yet." });
        return;
      }
      try {
        const svg = await draw(id, graph.mermaid);
        if (live) setShown({ svg });
      } catch (error) {
        if (live) setShown({ error: `Couldn't draw the graph: ${String(error)}` });
      }
    })();
    return () => {
      live = false;
    };
  }, [workflow, id]);
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[13px] text-[var(--muted)]">
        The graph LangGraph runs, node for node. Each node shows its step and its own name; a dashed edge is taken only
        when its label holds.
      </p>
      <div
        data-testid="compiled-graph"
        className="overflow-auto rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-none"
      >
        {shown === null && <span className="text-sm text-[var(--muted)]">Drawing…</span>}
        {shown && "error" in shown && <span className="text-sm text-[var(--danger)]">{shown.error}</span>}
        {/* Mermaid's own output, rendered with securityLevel strict: labels are escaped, no scripts. */}
        {shown && "svg" in shown && <div dangerouslySetInnerHTML={{ __html: shown.svg }} />}
      </div>
    </div>
  );
}
