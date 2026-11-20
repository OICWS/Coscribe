import { useCallback, useEffect, useRef, useState } from "react";
import { getCommands } from "./rest";
import type { CommandInfo } from "../types/session";

/** The slash commands, fetched again after each turn and on `refresh`: skills change while the
 * app runs (made in chat, in Settings or on disk). */
export function useSlashCommands(turnTick: number): [CommandInfo[], () => void] {
  const [commands, setCommands] = useState<CommandInfo[]>([]);
  const refresh = useCallback(() => void getCommands().then(setCommands), []);
  useEffect(refresh, [turnTick, refresh]);
  return [commands, refresh];
}

/** The composer's "/" menu: which commands match what is typed, and which one is highlighted. */
export function useCommandMenu(commands: CommandInfo[], text: string) {
  const [matches, setMatches] = useState<CommandInfo[]>([]);
  const [index, setIndex] = useState(-1);
  const itemRefs = useRef<(HTMLElement | null)[]>([]);

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

  // Enter runs the highlighted command, so it must stay in sight.
  useEffect(() => {
    itemRefs.current[index]?.scrollIntoView({ block: "nearest" });
  }, [index]);

  const move = (step: 1 | -1) => setIndex((i) => (i + step + matches.length) % matches.length);
  const itemRef = (i: number) => (el: HTMLElement | null) => void (itemRefs.current[i] = el);

  return { matches, index, open: matches.length > 0, update, hide, move, itemRef };
}
