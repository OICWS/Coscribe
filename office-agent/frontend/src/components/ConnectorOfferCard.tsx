import { useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ConnectorOffer } from "../lib/transcriptGrouping";
import { addMcpServer, getMcpCatalog, getMcpOAuthApps, getMcpServers, signInMcpServer } from "../lib/rest";
import type { McpCatalogEntry, McpServerInfo } from "../types/settings";
import { ConnectorOfferContext } from "./connectorOffers";
import { ConnectorIcon } from "./settings/ConnectorIcon";
import { SIGN_IN_TEXT } from "./settings/connectors/types";

const POLL_MS = 2500;
// Long enough for a guided setup in Settings and the sign-in after it; then the card stops asking.
const WATCH_MS = 10 * 60_000;
const BUTTON = "rounded-md px-2.5 py-1 text-[13px] disabled:opacity-50";
const SECONDARY = `${BUTTON} border border-[var(--border)] hover:bg-[var(--bg)]`;

interface Known {
  entry: McpCatalogEntry | null;
  info: McpServerInfo | null;
  /** The app a guided setup registers was saved, so Connect can sign in. */
  appSaved: boolean;
}

async function lookUp(name: string): Promise<Known> {
  const [catalog, servers, apps] = await Promise.all([getMcpCatalog(), getMcpServers(), getMcpOAuthApps()]);
  const entry = catalog.find((e) => e.name === name) ?? null;
  return { entry, info: servers[name] ?? null, appSaved: !entry?.setup || apps.saved.includes(entry.setup.group) };
}

/** Adds the entry as Settings > Connectors does, or signs in again to one added before whose
 * sign-in didn't finish; the error to show, if any. */
async function connectEntry(entry: McpCatalogEntry, added: boolean): Promise<string | null> {
  if (added) {
    const result = await signInMcpServer(entry.name);
    return result.connected || result.signin ? null : (result.error ?? "Couldn't sign in.");
  }
  const result = entry.server_url
    ? await addMcpServer(entry.name, { server_url: entry.server_url, auth: entry.auth, oauth_app: entry.setup?.group })
    : await addMcpServer(entry.name, { command: entry.command ?? "", args: entry.args ?? [] });
  const rejected = Object.values(result.rejected);
  if (rejected.length > 0) return `Not added: ${rejected[0]}`;
  return result.connected || result.signin ? null : (result.error ?? "Couldn't connect.");
}

/** Under a suggest_connector call (decision 0041): the connector the model asked for and why,
 * with Connect. Only the person's click adds it, and they sign in in their own browser; once it
 * is connected, or they say Not now, the card carries the conversation on. */
export function ConnectorOfferCard({ itemId, offer }: { itemId: string; offer: ConnectorOffer }) {
  const actions = useContext(ConnectorOfferContext);
  const [known, setKnown] = useState<Known | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answered, setAnswered] = useState(false);
  // Set by a click on this card (Connect, or a setup in Settings): only then does it watch for
  // the connection, for a while, so cards in an old conversation don't poll forever.
  const [watching, setWatching] = useState(false);
  const clicked = useRef(false);

  const refresh = useCallback(
    () =>
      lookUp(offer.name)
        .then(setKnown)
        .catch(() => {}),
    [offer.name],
  );
  useEffect(() => void refresh(), [refresh]);

  const connected = known?.info?.connected === true;
  const signingIn = !connected && Boolean(known?.info?.signin);
  useEffect(() => {
    if (!watching || connected) return;
    const id = setInterval(() => void refresh(), POLL_MS);
    const stop = setTimeout(() => setWatching(false), WATCH_MS);
    return () => {
      clearInterval(id);
      clearTimeout(stop);
    };
  }, [watching, connected, refresh]);

  const open = actions !== null && actions.openId === itemId && !answered;
  const busy = actions?.busy ?? true;
  const send = actions?.onSend;
  const answer = useCallback(
    (text: string) => {
      setAnswered(true);
      send?.(text);
    },
    [send],
  );
  // Carries on by itself only after this card's own Connect, while it is still the question in
  // front of the person.
  useEffect(() => {
    if (connected && clicked.current && open && !busy) {
      clicked.current = false;
      answer(`I connected ${offer.title}. Please continue.`);
    }
  }, [connected, open, busy, answer, offer.title]);

  if (!actions || !known?.entry) return null;
  const { entry } = known;
  const title = entry.title ?? entry.name;
  const needsSettings = entry.needs_config === true || !known.appSaved;

  const connect = async () => {
    clicked.current = true;
    setWatching(true);
    if (needsSettings) return actions.onOpenSettings(entry.name);
    setConnecting(true);
    setError(null);
    try {
      setError(await connectEntry(entry, known.info !== null));
      await refresh();
    } catch {
      setError("Couldn't connect. Try again, or add it in Settings > Connectors.");
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div
      className="mt-2 flex max-w-full flex-col gap-2 rounded-xl border border-[var(--border)] bg-[var(--card-bg)] px-3 py-2.5 text-sm"
      data-testid="connector-offer"
    >
      <div className="flex items-start gap-2.5">
        <ConnectorIcon name={entry.name} title={title} />
        <div className="min-w-0">
          <div className="font-medium">Connect {title}?</div>
          {offer.reason && <div className="mt-0.5 text-[13px]">{offer.reason}</div>}
          <div className="mt-0.5 text-[13px] text-[var(--muted)]">{entry.description}</div>
        </div>
      </div>
      <OfferControls
        state={connected ? "connected" : signingIn ? "signing-in" : "offered"}
        title={title}
        open={open}
        busy={busy}
        connecting={connecting}
        needsSettings={needsSettings}
        signInUrl={known.info?.signin?.url}
        onConnect={() => void connect()}
        onAnswer={answer}
      />
      {error && <div className="text-[13px] text-red-500">{error}</div>}
    </div>
  );
}

/** What the person can do now: carry on once connected, finish signing in, or Connect / Not now.
 * Answering is only for the card still in front of them (`open`). */
function OfferControls(props: {
  state: "connected" | "signing-in" | "offered";
  title: string;
  open: boolean;
  busy: boolean;
  connecting: boolean;
  needsSettings: boolean;
  signInUrl: string | undefined;
  onConnect: () => void;
  onAnswer: (text: string) => void;
}) {
  const { title, open, busy, connecting, needsSettings, onAnswer } = props;
  if (props.state === "connected") {
    return (
      <div className="flex items-center gap-3">
        <span className="text-[13px] text-[var(--success)]">Connected</span>
        {open && (
          <button
            type="button"
            disabled={busy}
            className={SECONDARY}
            onClick={() => onAnswer(`I connected ${title}. Please continue.`)}
          >
            Continue
          </button>
        )}
      </div>
    );
  }
  if (props.state === "signing-in") {
    return (
      <div className="text-[13px] text-[var(--muted)]">
        {SIGN_IN_TEXT}{" "}
        <a href={props.signInUrl} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">
          Open the sign-in page
        </a>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={connecting}
        className={`${BUTTON} bg-[var(--accent)] text-[var(--accent-fg)]`}
        onClick={props.onConnect}
      >
        {connecting ? "Connecting…" : needsSettings ? "Set up in Settings" : "Connect"}
      </button>
      {open && (
        <button
          type="button"
          disabled={busy || connecting}
          className={SECONDARY}
          onClick={() => onAnswer(`Not now. Please continue without ${title}.`)}
        >
          Not now
        </button>
      )}
      <span className="text-[13px] text-[var(--muted)]">
        {needsSettings ? "It needs a one-time setup first." : "You sign in in your own browser."}
      </span>
    </div>
  );
}
