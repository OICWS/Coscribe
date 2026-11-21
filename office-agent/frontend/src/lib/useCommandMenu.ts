import { useCallback, useEffect, useLayoutEffect, useRef, useState, type MutableRefObject } from "react";
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

/** A command the app runs itself instead of sending it: its handler, given what follows the name. */
export function appCommand(text: string, handlers: Record<string, (rest: string) => void>): (() => void) | null {
  const typed = /^\/([a-z-]+)(?:\s+([\s\S]*))?$/i.exec(text.trim());
  const name = typed?.[1].toLowerCase() ?? "";
  if (!typed || !Object.hasOwn(handlers, name)) return null;
  return () => handlers[name]((typed[2] ?? "").trim());
}

/** The composer's "/" menu: which commands match what is typed, and which one is highlighted. */
export function useCommandMenu(commands: CommandInfo[], text: string) {
  // One state, so a list fetched again and an arrow key pressed in the same moment both apply
  // to the latest highlight instead of one overwriting the other.
  const [menu, setMenu] = useState<{ matches: CommandInfo[]; index: number }>({ matches: [], index: -1 });
  const { matches, index } = menu;
  const listRef = useRef<HTMLDivElement | null>(null);
  const tipRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<(HTMLElement | null)[]>([]);
  const [tipTop, setTipTop] = useState(0);

  const closed = { matches: [], index: -1 };
  const hide = () => setMenu(closed);

  const listFor = (next: string, keep?: string) => {
    if (!next.startsWith("/") || next.includes(" ")) return closed;
    const prefix = next.slice(1).toLowerCase();
    const found = commands.filter((cmd) => cmd.name.toLowerCase().startsWith(prefix));
    // Nothing left to complete once the typed prefix is the only candidate's full name.
    if (found.length === 1 && found[0].name.toLowerCase() === prefix) return closed;
    return { matches: found, index: Math.max(keep ? found.findIndex((cmd) => cmd.name === keep) : -1, found.length > 0 ? 0 : -1) };
  };
  const update = (next: string) => setMenu(listFor(next));

  // A refetch can change the list under an open menu; the highlight stays on its command.
  useEffect(() => {
    setMenu((m) => listFor(text, m.matches[m.index]?.name));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commands]);

  // The description sits beside the highlighted row, outside the list, whose scrolling would clip
  // it; a long one is lifted to end where the list ends rather than run over the message box.
  const placeTip = useCallback(() => {
    const item = itemRefs.current[index];
    const list = listRef.current;
    if (!item || !list) return;
    const lowest = list.offsetHeight - (tipRef.current?.offsetHeight ?? 0);
    setTipTop(Math.max(0, Math.min(item.offsetTop - list.scrollTop, lowest)));
  }, [index]);

  // Enter runs the highlighted command, so it must stay in sight.
  useLayoutEffect(() => {
    itemRefs.current[index]?.scrollIntoView({ block: "nearest" });
    placeTip();
  }, [index, placeTip]);

  const move = (step: 1 | -1) => setMenu((m) => ({ ...m, index: (m.index + step + m.matches.length) % m.matches.length }));
  const setIndex = (i: number) => setMenu((m) => ({ ...m, index: i }));
  const itemRef = (i: number) => (el: HTMLElement | null) => void (itemRefs.current[i] = el);

  return { matches, index, setIndex, open: matches.length > 0, update, hide, move, itemRef, listRef, tipRef, tipTop, placeTip };
}
