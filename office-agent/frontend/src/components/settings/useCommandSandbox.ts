import { useCallback, useEffect, useRef, useState } from "react";
import { getCommandSandbox, removeCommandSandbox, setUpCommandSandbox } from "../../lib/rest";
import type { CommandSandbox, CommandSandboxMode } from "../../types/settings";

const POLL_MS = 1000;

/** The command sandbox's state, polled while it is being set up or removed so each step shows. */
export function useCommandSandbox(active: boolean) {
  const [sandbox, setSandbox] = useState<CommandSandbox | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  const stopPolling = () => {
    if (timer.current !== null) window.clearInterval(timer.current);
    timer.current = null;
  };
  const poll = useCallback(() => {
    stopPolling();
    timer.current = window.setInterval(() => {
      getCommandSandbox().then(
        (next) => {
          setSandbox((prev) => (prev?.state === "working" || next.state === "working" ? next : prev));
          if (next.state !== "working") stopPolling();
        },
        () => undefined,
      );
    }, POLL_MS);
  }, []);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getCommandSandbox().then(
      (result) => {
        if (cancelled) return;
        setSandbox(result);
        // Set up started before this page opened (or in another window): follow it.
        if (result.state === "working") poll();
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [active, poll]);

  const run = async (action: () => Promise<CommandSandbox | { error: string }>, follow: boolean) => {
    setBusy(true);
    if (follow) poll();
    try {
      const result = await action();
      setSandbox("state" in result ? result : { state: "failed", detail: result.error });
    } catch (err) {
      setSandbox({ state: "failed", detail: err instanceof Error ? err.message : "" });
    } finally {
      stopPolling();
      setBusy(false);
    }
  };

  return {
    sandbox,
    busy: busy || sandbox?.state === "working",
    setUp: (mode: CommandSandboxMode) => void run(() => setUpCommandSandbox(mode), true),
    remove: () => void run(removeCommandSandbox, true),
  };
}
