import { useEffect, useRef, useState } from "react";
import { flashSetting } from "./flashSetting";
import type { SettingsCategory } from "./SettingsModal";

/** A picked setting: its page opens first, then the row is scrolled to and flashed once it has rendered.
 * `content` goes on the element that holds the page. */
export function useSettingTarget(category: SettingsCategory) {
  const [target, setTarget] = useState<{ category: SettingsCategory; label: string } | null>(null);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!target || category !== target.category) return;
    let cancelled = false;
    // A page that loads its rows from the server renders them a moment later.
    const deadline = performance.now() + 2000;
    const look = () => {
      if (cancelled || !content.current) return;
      flashSetting(target.label, content.current).then((found) => {
        if (cancelled) return;
        if (found || performance.now() > deadline) setTarget(null);
        else window.setTimeout(look, 100);
      });
    };
    look();
    return () => {
      cancelled = true;
    };
  }, [target, category]);
  return { setTarget, content };
}
