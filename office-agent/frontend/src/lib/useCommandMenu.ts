import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { getCommands, setThreadMeta } from "./rest";
import { startNewThread } from "./nav";
import type { CommandInfo } from "../types/session";
import type { AgentSocket } from "./ws";

/** Typed commands the menu leaves out because a control does the same; typed, they still run. */
const UNLISTED_COMMANDS = ["plan", "accept-edits", "auto", "stop", "saveworkflow"];

/** True for a known command, listed or not: during a reply one is held instead of being sent
 * to the model as a note. */
export function isCommand(text: string, commands: CommandInfo[]): boolean {
  const word = /^\/(\S+)/.exec(text.trim())?.[1]?.toLowerCase();
  return !!word && (UNLISTED_COMMANDS.includes(word) || commands.some((cmd) => cmd.name.toLowerCase() === word));
}

/** The slash commands, fetched again after each turn and on `refresh`: skills change while the
 * app runs (made in chat, in Settings or on disk). */
export function useSlashCommands(turnTick: number): [CommandInfo[], () => void] {
  const [commands, setCommands] = useState<CommandInfo[]>([]);
  const refresh = useCallback(() => void getCommands().then(setCommands), []);
  useEffect(refresh, [turnTick, refresh]);
  return [commands, refresh];
}

// Outlives the switch to the new thread, which remounts what holds it.
let carriedEnvironment: { threadId: string; environment: string } | null = null;

/** /clear in the app: the conversation is archived, not erased, and a blank one opens in the same
 * environment. Call after the socket effect, so the send goes to the new thread's socket. */
export function useClearToNewChat(
  threadId: string,
  environment: string,
  socketRef: MutableRefObject<AgentSocket | null>,
) {
  useEffect(() => {
    if (carriedEnvironment?.threadId !== threadId) return;
    socketRef.current?.send({ type: "set_environment", environment: carriedEnvironment.environment });
    carriedEnvironment = null;
  }, [threadId, socketRef]);

  return () => {
    void setThreadMeta(threadId, { archived: true });
    const next = startNewThread();
    if (environment) carriedEnvironment = { threadId: next, environment };
  };
}

/** The composer's "/" menu: which commands match what is typed, and which one is highlighted. */
export function useCommandMenu(commands: CommandInfo[], text: string) {
  const [matches, setMatches] = useState<CommandInfo[]>([]);
  const [index, setIndex] = useState(-1);
  const listRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<(HTMLElement | null)[]>([]);
  const [tipTop, setTipTop] = useState(0);

  const hide = () => {
    setMatches([]);
    setIndex(-1);
  };

  const update = (next: string) => {
    if (!next.startsWith("/") || next.includes(" ")) return hide();
    const prefix = next.slice(1).toLowerCase();
    const found = commands.filter((cmd) => cmd.name.toLowerCase().startsWith(prefix));
    // Nothing left to complete once the typed prefix is the only candidate's full name.
    if (found.length === 1 && found[0].name.toLowerCase() === prefix) return hide();
    setMatches(found);
    setIndex(found.length > 0 ? 0 : -1);
  };

  // A refetch can change the list under an open menu.
  useEffect(() => {
    update(text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commands]);

  // The description sits beside the highlighted row, outside the list, whose scrolling would clip it.
  const placeTip = useCallback(() => {
    const item = itemRefs.current[index];
    if (item && listRef.current) setTipTop(item.offsetTop - listRef.current.scrollTop);
  }, [index]);

  // Enter runs the highlighted command, so it must stay in sight.
  useEffect(() => {
    itemRefs.current[index]?.scrollIntoView({ block: "nearest" });
    placeTip();
  }, [index, placeTip]);

  const move = (step: 1 | -1) => setIndex((i) => (i + step + matches.length) % matches.length);
  const itemRef = (i: number) => (el: HTMLElement | null) => void (itemRefs.current[i] = el);

  return { matches, index, setIndex, open: matches.length > 0, update, hide, move, itemRef, listRef, tipTop, placeTip };
}
