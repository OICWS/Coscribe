import type { ComponentType, SVGProps } from "react";
import { createPortal } from "react-dom";
import { inputCards, modelFacts, outputCards, providerCards } from "../lib/modelMarks";
import type { ModelRow } from "../types/settings";
import { EyeIcon, FileTextIcon, GlobeIcon } from "./icons";
import { ImageIcon, MicIcon, VideoIcon } from "./modelIcons";

export interface ModelTipAnchor {
  rect: DOMRect;
  row: ModelRow;
  /** The provider's title, shown after the model's name. */
  provider: string;
  /** Where it goes when there is room: a submenu opening to the left keeps its tips there too. */
  side?: "left" | "right";
}

const WIDTH = 300;
const GAP = 8;

const CARD_ICONS: Record<string, ComponentType<SVGProps<SVGSVGElement>>> = {
  Vision: EyeIcon,
  PDF: FileTextIcon,
  Audio: MicIcon,
  Video: VideoIcon,
  Image: ImageIcon,
  "Web search": GlobeIcon,
};

function Cards({ title, labels }: { title: string; labels: string[] }) {
  if (labels.length === 0) return null;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-[11px] opacity-60">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {labels.map((label) => {
          const Icon = CARD_ICONS[label];
          return (
            <span key={label} className="flex items-center gap-1.5 rounded-md bg-[color-mix(in_srgb,var(--bg)_16%,transparent)] px-2 py-1 text-xs">
              {Icon && <Icon className="h-3.5 w-3.5" />}
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** What a hovered model can do, beside it: fixed to the viewport, so a menu's or a list's own
 * scrolling can't clip it; on the other side when the preferred one has no room. */
export function ModelTip({ tip }: { tip: ModelTipAnchor | null }) {
  if (!tip) return null;
  const { rect, row, provider } = tip;
  const roomRight = rect.right + GAP + WIDTH <= window.innerWidth;
  const roomLeft = rect.left - GAP - WIDTH >= 0;
  const onLeft = tip.side === "left" ? roomLeft || !roomRight : !roomRight;
  const style = {
    top: rect.top + rect.height / 2,
    width: WIDTH,
    ...(onLeft ? { right: window.innerWidth - rect.left + GAP } : { left: rect.right + GAP }),
  };
  return createPortal(
    <div
      role="tooltip"
      className="pointer-events-none fixed z-[1000] flex -translate-y-1/2 flex-col gap-3 rounded-xl bg-[var(--fg)] px-3.5 py-3 text-[13px] leading-snug text-[var(--bg)] shadow-[var(--shadow)]"
      style={style}
    >
      <div>
        <span className="font-medium">{row.name}</span>
        <span className="opacity-60"> · {provider}</span>
      </div>
      {row.known ? (
        <>
          <Cards title="Native input" labels={inputCards(row)} />
          <Cards title="Native output" labels={outputCards(row)} />
          {modelFacts(row).length > 0 && (
            <div className="flex flex-col gap-0.5 opacity-80">
              {modelFacts(row).map((fact) => (
                <div key={fact}>{fact}</div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="opacity-80">Not in the bundled catalog, so what it can do is unknown.</div>
      )}
      <Cards title="Through the provider" labels={providerCards(row)} />
    </div>,
    document.body,
  );
}
