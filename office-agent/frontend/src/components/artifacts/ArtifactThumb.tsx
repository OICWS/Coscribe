import { useState } from "react";
import { KINDS, thumbnailUrl, type ArtifactKind, type ArtifactSummary } from "../../lib/artifacts";
import { KindIcon } from "./artifactIcons";

/** A kind's colour at `percent`, over the page's own background. */
export const tinted = (kind: ArtifactKind, percent: number) => `color-mix(in srgb, ${KINDS[kind].colour} ${percent}%, var(--bg))`;

/** The kind's mark: its icon on a tile of its colour. */
export function KindTile({ kind, size }: { kind: ArtifactKind; size: "sm" | "md" | "lg" }) {
  const box = { sm: "h-5 w-5 rounded-md", md: "h-9 w-9 rounded-xl", lg: "h-12 w-12 rounded-xl" }[size];
  const icon = { sm: "h-3 w-3", md: "h-5 w-5", lg: "h-6 w-6" }[size];
  return (
    <span className={`flex shrink-0 items-center justify-center ${box}`} style={{ background: tinted(kind, 16), color: KINDS[kind].colour }}>
      <KindIcon kind={kind} className={icon} />
    </span>
  );
}

/** What a card shows of an artifact: a deck's first slide, a document's opening lines, and for the
 * rest a stand-in drawn in the kind's colour. */
export function Thumbnail({ item }: { item: ArtifactSummary }) {
  const [failed, setFailed] = useState(false);
  const base = "relative aspect-[16/9] w-full overflow-hidden";
  const colour = KINDS[item.kind].colour;
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
  if (item.kind === "sheets") {
    return (
      <div className={`${base} flex items-center justify-center`} style={{ background: tinted("sheets", 8) }}>
        <div className="grid w-[62%] grid-cols-4 overflow-hidden rounded-lg border border-white bg-white shadow-sm">
          {Array.from({ length: 20 }, (_, i) => (
            <span key={i} className="h-[18px] border-b border-r border-[#e7e5e2]" style={i < 4 ? { background: `color-mix(in srgb, ${colour} 22%, white)` } : undefined} />
          ))}
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
