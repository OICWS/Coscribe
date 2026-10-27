import { useEffect, useRef } from "react";
import type { LogItem } from "../state/reducer";
import { replyToDocComment } from "./docComments";
import { replyToComment, type CommentLink } from "./slideComments";

/** The longest reply the comment store takes. */
const MAX_REPLY = 4000;

/** coscribe's answer to the message `text` in the log: the last thing it said in that turn.
 * Null while the message has not been sent yet or its turn said nothing. */
export function answerFor(items: LogItem[], text: string, from: number): string | null {
  const asked = items.findIndex((item, i) => i >= from && item.kind === "user" && item.text === text);
  if (asked < 0) return null;
  let answer: string | null = null;
  for (const item of items.slice(asked + 1)) {
    if (item.kind === "user") break;
    if (item.kind === "agent" && !item.streaming && item.text.trim()) answer = item.text.trim();
  }
  return answer && answer.length > MAX_REPLY ? `${answer.slice(0, MAX_REPLY - 1)}…` : answer;
}

interface Waiting {
  threadId: string;
  text: string;
  from: number;
  link: CommentLink;
}

/** Sends a comment to coscribe as a message through `send`, and posts coscribe's answer as the
 * comment's reply once that turn ends. */
export function useCommentSender(threadId: string, items: LogItem[], turnInFlight: boolean, send: (text: string) => void) {
  const waiting = useRef<Waiting[]>([]);
  const busy = useRef(turnInFlight);
  useEffect(() => {
    const ended = busy.current && !turnInFlight;
    busy.current = turnInFlight;
    if (!ended) return;
    waiting.current = waiting.current.filter((entry) => {
      if (entry.threadId !== threadId) return true;
      const answer = answerFor(items, entry.text, entry.from);
      if (answer === null) return true;
      const { path, commentId, doc, alsoCommentIds = [] } = entry.link;
      for (const id of [commentId, ...alsoCommentIds]) {
        const reply = doc ? replyToDocComment : replyToComment;
        void reply(threadId, path, id, answer, true).catch(() => undefined);
      }
      return false;
    });
  }, [threadId, items, turnInFlight]);
  // A message without a link is a question about the file, not a comment waiting for an answer.
  return (text: string, link?: CommentLink) => {
    if (!link) return send(text);
    waiting.current.push({ threadId, text, from: items.length, link });
    send(text);
  };
}
