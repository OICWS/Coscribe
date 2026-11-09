

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

/** A connector a chat card asked Settings to open at, taken once by the Connectors tab when it
 * opens, so a card can bring the person to a guided setup without a prop through every layer. */
let toOpen: string | null = null;
export function openConnectorNext(name: string) {
  toOpen = name;
}

export function takeConnectorToOpen(): string | null {
  const name = toOpen;
  toOpen = null;
  return name;
}
