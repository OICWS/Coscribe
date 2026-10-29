import { useEffect, useRef, useState } from "react";
import { PAGE_KINDS, designUrl, thumbnailUrl, type ArtifactSummary, type PageItem, type PageKind } from "../../lib/artifacts";
import { KindIcon } from "./artifactIcons";

/** A kind's colour at `percent`, over the page's own background. */
export const tinted = (kind: PageKind, percent: number) => `color-mix(in srgb, ${PAGE_KINDS[kind].colour} ${percent}%, var(--bg))`;

/** The kind's mark: its icon on a tile of its colour. */
export function KindTile({ kind, size }: { kind: PageKind; size: "sm" | "md" | "lg" }) {
  const box = { sm: "h-5 w-5 rounded-md", md: "h-9 w-9 rounded-xl", lg: "h-12 w-12 rounded-xl" }[size];
  const icon = { sm: "h-3 w-3", md: "h-5 w-5", lg: "h-6 w-6" }[size];
  return (
    <span className={`flex shrink-0 items-center justify-center ${box}`} style={{ background: tinted(kind, 16), color: PAGE_KINDS[kind].colour }}>
      <KindIcon kind={kind} className={icon} />
    </span>
  );
}

/** What a card shows of an artifact: a deck's first slide, a document's opening lines, and for the
 * rest a stand-in drawn in the kind's colour. */
export function Thumbnail({ item }: { item: PageItem }) {
  const [failed, setFailed] = useState(false);
  const base = "relative aspect-[16/9] w-full overflow-hidden";
  const colour = PAGE_KINDS[item.kind].colour;
  if (item.kind === "design-system") return <SwatchThumb palette={item.palette} base={base} />;
  if (item.kind === "slides" && !failed) {
    return (
      <div className={`${base} bg-white`}>
        <img
          src={thumbnailUrl(item)}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }
  if ((item.kind === "design" || item.kind === "dashboard") && !failed) {
    return <DesignThumb item={item} base={base} />;
  }
  if (item.kind === "docs") {
    return (
      <div className={base} style={{ background: tinted("docs", 8) }}>
        {/* The page is white in both themes: it stands for paper. */}
        <div className="absolute inset-x-[11%] bottom-0 top-5 overflow-hidden rounded-t-lg bg-white px-5 pt-4 shadow-sm">
          <div className="line-clamp-2 text-[15px] leading-snug text-[#201e1d]" style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
            {item.excerpt?.heading ?? item.name}
          </div>
          {item.excerpt?.text && <div className="mt-2 line-clamp-5 text-[11px] leading-relaxed text-[#6b6866]">{item.excerpt.text}</div>}
        </div>
      </div>
    );
  }
  return (
    <div className={`${base} flex items-center justify-center`} style={{ background: tinted(item.kind, 10), color: colour }}>
      <KindIcon kind={item.kind} className="h-9 w-9" />
    </div>
  );
}

/** A design system's colors, side by side; the system's own, so they stay as they are in both themes. */
function SwatchThumb({ palette, base }: { palette: string[]; base: string }) {
  return (
    <div className={`${base} flex`} style={{ background: tinted("design-system", 10) }}>
      {palette.length === 0 ? (
        <div className="flex flex-1 items-center justify-center" style={{ color: PAGE_KINDS["design-system"].colour }}>
          <KindIcon kind="design-system" className="h-9 w-9" />
        </div>
      ) : (
        palette.map((colour, i) => <span key={`${colour}${i}`} className="h-full flex-1" style={{ background: colour }} />)
      )}
    </div>
  );
}

/** The page's own width and height when the thumbnail draws it, scaled down to the card. */
const DESIGN_VIEW = { width: 1280, height: 720 };

/** A design card shows the page itself, drawn small in the same sandbox the panel uses. */
function DesignThumb({ item, base }: { item: ArtifactSummary; base: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const fit = () => setScale(el.clientWidth / DESIGN_VIEW.width);
    fit();
    const watcher = new ResizeObserver(fit);
    watcher.observe(el);
    return () => watcher.disconnect();
  }, []);
  return (
    <div ref={box} className={`${base} bg-white`}>
      {scale > 0 && (
        <iframe
          title={item.name}
          src={designUrl(item)}
          sandbox="allow-scripts"
          loading="lazy"
          tabIndex={-1}
          aria-hidden="true"
          className="pointer-events-none absolute left-0 top-0 origin-top-left border-0"
          style={{ width: DESIGN_VIEW.width, height: DESIGN_VIEW.height, transform: `scale(${scale})` }}
        />
      )}
    </div>
  );
}
