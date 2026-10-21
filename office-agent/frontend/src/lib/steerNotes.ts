import { useEffect, useRef, type Dispatch } from "react";
import type { ChatAction, ChatState, LogItem } from "../state/reducer";
import type { WsClientMessage } from "../types/wire";

/** What a note sent while the reply is being worked on can still do. */
export interface SteerActions {
  withdraw: (id: string) => void;
  /** Interrupts the reply and sends the unread notes as the next message. */
  sendNow: () => void;
}

type Note = Extract<LogItem, { kind: "steer" }>;

/** Notes sent while a reply is being worked on: sending one, taking it back, stopping the reply
 * (which hands the unread ones back to the composer) and interrupting it to send them now. */
export function useSteerNotes(
  state: ChatState,
  dispatch: Dispatch<ChatAction>,
  send: (message: WsClientMessage) => void,
  toComposer: (text: string) => void,
  sendMessage: (payload: { displayText: string; outgoingText: string; isInstant: boolean }) => void,
) {
  // The unread notes, held until the stopped reply has ended, then sent as a message of their own.
  const afterStop = useRef<string | null>(null);
  useEffect(() => {
    const text = afterStop.current;
    if (text === null || state.turnInFlight) return;
    afterStop.current = null;
    sendMessage({ displayText: text, outgoingText: text, isInstant: false });
  }, [state.turnInFlight]);

  const unread = () => state.items.filter((item): item is Note => item.kind === "steer" && item.status === "pending");
  const drop = (notes: Note[]) => dispatch({ type: "local_steers_withdrawn", ids: notes.map((note) => note.id) });
  const joined = (notes: Note[]) => notes.map((note) => note.text).join("\n\n");

  const actions: SteerActions = {
    withdraw: (id) => {
      const note = unread().find((item) => item.id === id);
      if (!note) return;
      drop([note]);
      toComposer(note.text);
      send({ type: "steer", id, text: null });
    },
    sendNow: () => {
      const notes = unread();
      if (notes.length === 0) return;
      drop(notes);
      const text = joined(notes);
      // A reply that ended meanwhile has no end left to wait for.
      if (!state.turnInFlight) {
        sendMessage({ displayText: text, outgoingText: text, isInstant: false });
        return;
      }
      afterStop.current = text;
      send({ type: "stop" });
    },
  };
  return {
    actions,
    steer: (text: string) => {
      const id = `steer-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      dispatch({ type: "local_steer", id, text });
      send({ type: "steer", id, text });
    },
    stop: () => {
      const notes = unread();
      if (notes.length > 0) {
        drop(notes);
        toComposer(joined(notes));
      }
      send({ type: "stop" });
    },
  };
}
