import { useEffect, useRef, useState, type Dispatch } from "react";
import type { ChatAction, ChatState, LogItem } from "../state/reducer";
import type { WsClientMessage } from "../types/wire";

/** What a note sent while the reply is being worked on can still do. */
export interface SteerActions {
  withdraw: (id: string) => void;
  /** Interrupts the reply and sends the unread notes as the next message. */
  sendNow: () => void;
}

/** A note as the composer hands it over: what the chat shows, what the model reads, and the
 * pictures (data URLs) and workspace files attached to it. */
export interface SteerDraft {
  displayText: string;
  outgoingText: string;
  images?: string[];
  files?: string[];
}

/** What goes back into the composer: the text and the attachments, to edit and send again. */
export interface ComposerDraft {
  text: string;
  images?: string[];
  files?: string[];
}

type MessagePayload = { displayText: string; outgoingText: string; images?: string[]; files?: string[]; isInstant: boolean };

type Note = Extract<LogItem, { kind: "steer" }>;

const nonEmpty = (list: string[]) => (list.length > 0 ? list : undefined);

/** Several notes as one message, attachments included. */
function asMessage(notes: Note[]): MessagePayload {
  return {
    displayText: notes.map((note) => note.text).join("\n\n"),
    outgoingText: notes.map((note) => note.outgoingText ?? note.text).join("\n\n"),
    images: nonEmpty(notes.flatMap((note) => note.images ?? [])),
    files: nonEmpty(notes.flatMap((note) => note.files ?? [])),
    isInstant: false,
  };
}

/** Notes sent while a reply is being worked on: sending one, taking it back, stopping the reply
 * (which hands the unread ones back to the composer) and interrupting it to send them now. */
export function useSteerNotes(
  state: ChatState,
  dispatch: Dispatch<ChatAction>,
  send: (message: WsClientMessage) => void,
  toComposer: (draft: ComposerDraft) => void,
  sendMessage: (payload: MessagePayload) => void,
) {
  // The unread notes, held until the stopped reply has ended, then sent as a message of their own.
  const afterStop = useRef<MessagePayload | null>(null);
  // Stop was pressed and the reply has not ended yet: a model call in flight can take a moment.
  const [stopping, setStopping] = useState(false);
  useEffect(() => {
    if (!state.turnInFlight) setStopping(false);
    const message = afterStop.current;
    if (message === null || state.turnInFlight) return;
    afterStop.current = null;
    sendMessage(message);
  }, [state.turnInFlight]);

  const unread = () => state.items.filter((item): item is Note => item.kind === "steer" && item.status === "pending");
  const drop = (notes: Note[]) => dispatch({ type: "local_steers_withdrawn", ids: notes.map((note) => note.id) });
  // A stop denies what is waiting for approval on the server; the cards follow at once.
  const denyApprovals = () =>
    state.items.forEach((item) => {
      if (item.kind === "approval" && item.status === "pending") dispatch({ type: "local_approval_resolved", id: item.id, approved: false });
    });
  const backToComposer = (notes: Note[]) => {
    const message = asMessage(notes);
    toComposer({ text: message.displayText, images: message.images, files: message.files });
  };

  const actions: SteerActions = {
    withdraw: (id) => {
      const note = unread().find((item) => item.id === id);
      if (!note) return;
      drop([note]);
      backToComposer([note]);
      send({ type: "steer", id, text: null });
    },
    sendNow: () => {
      const notes = unread();
      if (notes.length === 0) return;
      drop(notes);
      const message = asMessage(notes);
      // A reply that ended meanwhile has no end left to wait for.
      if (!state.turnInFlight) {
        sendMessage(message);
        return;
      }
      afterStop.current = message;
      denyApprovals();
      setStopping(true);
      send({ type: "stop" });
    },
  };
  const question = state.items.findLast((item) => item.kind === "question" && item.status === "pending");
  const approval = state.items.findLast((item) => item.kind === "approval" && item.status === "pending");
  return {
    actions,
    stopping,
    /** A note for the running reply; while a question or an approval card waits, the reply is
     * stuck on it, so plain text answers the question or denies the call with these words. A note
     * with attachments can't be such an answer, so it waits as a note for after the card. */
    steer: (draft: SteerDraft) => {
      const text = draft.outgoingText;
      const attached = (draft.images?.length ?? 0) > 0 || (draft.files?.length ?? 0) > 0;
      if (question && !attached) {
        dispatch({ type: "local_question_answered", id: question.id, answers: [], reply: text });
        send({ type: "question_response", id: question.id, reply: text });
        return;
      }
      if (approval && !attached) {
        dispatch({ type: "local_approval_resolved", id: approval.id, approved: false, reply: text });
        send({ type: "approval_response", id: approval.id, approved: false, reply: text });
        return;
      }
      const id = `steer-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      dispatch({
        type: "local_steer",
        id,
        text: draft.displayText,
        ...(text !== draft.displayText ? { outgoingText: text } : {}),
        ...(draft.images?.length ? { images: draft.images } : {}),
        ...(draft.files?.length ? { files: draft.files } : {}),
      });
      send({ type: "steer", id, text, ...(draft.images?.length ? { images: draft.images } : {}) });
    },
    stop: () => {
      const notes = unread();
      if (notes.length > 0) {
        drop(notes);
        backToComposer(notes);
      }
      denyApprovals();
      setStopping(true);
      send({ type: "stop" });
    },
  };
}
