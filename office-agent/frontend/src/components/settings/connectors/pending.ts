

/** Module-level: a first `npx` install can take a minute or more, and the
 * add keeps running after Settings closes or the tab changes, so its
 * "connecting" marker has to outlive this component. */
export const pendingConnectorAdds = new Set<string>();
let listeners: (() => void)[] = [];
export function notifyPendingChanged() {
  for (const listener of listeners) listener();
}

export function subscribePendingChanged(listener: () => void): () => void {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}
