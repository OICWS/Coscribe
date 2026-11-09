import { createContext } from "react";

/** What a connector card in the chat can do (decision 0041). Unset outside a chat, where no
 * card is shown. */
export interface ConnectorOfferActions {
  /** A reply is being generated; the card waits to answer for the person. */
  busy: boolean;
  /** The card that may still answer for the person; see openConnectorOfferId. */
  openId: string | null;
  /** Sends a message as the person, to carry the conversation on. */
  onSend: (text: string) => void;
  /** Opens Settings at the connector, for one that needs a one-time setup first. */
  onOpenSettings: (name: string) => void;
}

export const ConnectorOfferContext = createContext<ConnectorOfferActions | null>(null);
