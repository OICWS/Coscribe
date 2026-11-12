import { useContext, useEffect, useState } from "react";
import { declineConnectorOffer, getMcpServers } from "../../lib/rest";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import type { ConnectorOfferEntry } from "../../lib/transcriptGrouping";
import { ConnectorIcon } from "../settings/ConnectorIcon";
import { CheckCircleIcon } from "../icons";
import { ThreadIdContext } from "../threadContext";
import { OpenConnector } from "./contexts";

type Status = "offered" | "opened" | "connected" | "declined";

const POLL_MS = 3000;

/** A connector the conversation suggested. Connecting happens on its page in Settings >
 * Connectors, like any connection; the card only follows it, and the server wakes the
 * conversation once it is connected. */
export function ConnectorOfferCard({ entry }: { entry: ConnectorOfferEntry }) {
  const threadId = useContext(ThreadIdContext);
  const openConnector = useContext(OpenConnector);
  const [status, setStatus] = useState<Status>("offered");

  // Checked once when shown, then polled only after the person opened its page, so the old
  // cards of a long conversation don't keep asking.
  useEffect(() => {
    if (status === "connected" || status === "declined") return;
    let alive = true;
    const check = () =>
      getMcpServers()
        .then((servers) => {
          if (alive && servers[entry.name]?.connected) setStatus("connected");
        })
        .catch(() => {});
    check();
    const id = status === "opened" ? setInterval(check, POLL_MS) : undefined;
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [status, entry.name]);

  const open = () => {
    setStatus("opened");
    openConnector?.(entry.name);
  };

  const decline = () => {
    setStatus("declined");
    void declineConnectorOffer(threadId, entry.name).catch(() => {});
  };

  const signedOut = entry.state === "signed_out";
  return (
    <div role="region" aria-label={`Connect ${entry.title}`} className="flex max-w-[640px] flex-col gap-3 rounded-xl border border-[var(--border)] px-4 py-3 text-sm">
      <div className="flex items-start gap-3">
        <ConnectorIcon name={entry.name} title={entry.title} size="md" />
        <div className="min-w-0 flex-1">
          <div className="font-medium">{signedOut ? `Sign in to ${entry.title} again` : `Connect ${entry.title}`}</div>
          {entry.why && <div className="mt-0.5 [overflow-wrap:anywhere]">{entry.why}</div>}
          <div className="mt-1 text-xs text-[var(--muted)]">
            {entry.description}
            {entry.toolCount > 0 && ` · ${entry.toolCount} tools`}
          </div>
        </div>
      </div>
      {status === "connected" ? (
        <div className="flex items-center gap-1.5 text-[13px] text-[var(--success)]">
          <CheckCircleIcon className="h-4 w-4 shrink-0" />
          {entry.title} connected
        </div>
      ) : status === "declined" ? (
        <div className="text-[13px] text-[var(--muted)]">Not now. You can connect it any time in Settings &gt; Connectors.</div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={primaryButton} onClick={open}>
            {signedOut ? "Sign in again" : "Connect"}
          </button>
          <button type="button" className={secondaryButton} onClick={decline}>
            Not now
          </button>
          {status === "opened" && <span className="text-xs text-[var(--muted)]">I'll carry on here once it's connected.</span>}
        </div>
      )}
    </div>
  );
}

// Mirrors conversation/connector_offer.py's connected_note.
export const CONNECTED_NOTE_PREFIX = "[Connector connected]";

/** Stands in for the message a conversation gets once a connector it offered is connected. */
export function ConnectorConnectedNote({ text }: { text: string }) {
  const title = /connected (.*?), which you offered/.exec(text)?.[1] ?? "The connector";
  return (
    <div className="flex items-center gap-2 self-start text-[13px] text-[var(--muted)]">
      <CheckCircleIcon className="h-4 w-4 shrink-0 text-[var(--success)]" />
      {title} is connected. Carrying on with your request.
    </div>
  );
}
