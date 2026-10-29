import { useRef, useState } from "react";
import { PAGE_KINDS, PAGE_ORDER, type PageKind } from "../../lib/artifacts";
import { useClickOutside } from "../../lib/useClickOutside";
import { tinted } from "./ArtifactThumb";

/** A small drawing of each kind, on the kind's colour. */
function Illustration({ kind }: { kind: PageKind }) {
  const colour = PAGE_KINDS[kind].colour;
  const bar = (width: string, strong = false) => (
    <span className="block h-1.5 rounded-full" style={{ width, background: strong ? colour : `color-mix(in srgb, ${colour} 28%, white)` }} />
  );
  return (
    <div
      className="flex aspect-[16/10] items-center justify-center"
      style={{ background: `linear-gradient(180deg, ${tinted(kind, 20)}, ${tinted(kind, 7)})` }}
    >
      {kind === "docs" && (
        <div className="flex h-[78%] w-[40%] flex-col gap-1.5 rounded-lg border border-white bg-white p-2.5 shadow-sm">
          {bar("60%", true)}
          {bar("100%")}
          {bar("100%")}
          {bar("75%")}
        </div>
      )}
      {kind === "slides" && (
        <div className="flex h-[62%] w-[72%] items-center gap-2.5 rounded-lg border border-white bg-white p-3 shadow-sm">
          <div className="flex flex-1 flex-col gap-1.5">
            {bar("90%", true)}
            {bar("65%")}
            {bar("80%")}
          </div>
          <span className="h-[70%] w-[26%] rounded-md" style={{ background: `color-mix(in srgb, ${colour} 30%, white)` }} />
        </div>
      )}
      {kind === "design" && (
        <div className="relative h-[68%] w-[72%] overflow-hidden rounded-lg border border-white bg-white shadow-sm">
          <span className="absolute left-[10%] top-[22%] h-[40%] w-[30%] rounded-full" style={{ background: `color-mix(in srgb, ${colour} 28%, white)` }} />
          <span className="absolute left-[46%] top-[16%] h-[54%] w-[44%] rounded-md" style={{ background: `color-mix(in srgb, ${colour} 55%, white)` }} />
          <span className="absolute left-[42%] top-[10%] h-[66%] w-[52%] rounded-sm border border-dashed" style={{ borderColor: colour }} />
          {["left-[42%] top-[10%]", "left-[94%] top-[10%]", "left-[42%] top-[76%]", "left-[94%] top-[76%]"].map((at) => (
            <span key={at} className={`absolute ${at} h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-[2px] border bg-white`} style={{ borderColor: colour }} />
          ))}
        </div>
      )}
      {kind === "design-system" && (
        <div className="flex h-[62%] w-[72%] overflow-hidden rounded-lg border border-white bg-white shadow-sm">
          {[100, 70, 45, 22].map((share) => (
            <span key={share} className="flex-1" style={{ background: `color-mix(in srgb, ${colour} ${share}%, white)` }} />
          ))}
        </div>
      )}
      {kind === "dashboard" && (
        <div className="flex h-[72%] w-[72%] flex-col gap-1.5 rounded-lg border border-white bg-white p-2 shadow-sm">
          <div className="flex gap-2">
            {[true, false].map((strong) => (
              <div key={String(strong)} className="flex flex-1 flex-col gap-0.5 rounded-md px-1.5 py-1" style={{ background: `color-mix(in srgb, ${colour} 12%, white)` }}>
                {bar("45%")}
                <span className="block h-1.5 rounded-full" style={{ width: "70%", background: strong ? colour : `color-mix(in srgb, ${colour} 55%, white)` }} />
              </div>
            ))}
          </div>
          <svg viewBox="0 0 100 32" preserveAspectRatio="none" className="min-h-0 w-full flex-1" aria-hidden>
            <path d="M0 26 L18 18 L36 22 L56 10 L78 14 L100 3 L100 32 L0 32 Z" fill={`color-mix(in srgb, ${colour} 18%, white)`} />
            <path d="M0 26 L18 18 L36 22 L56 10 L78 14 L100 3" fill="none" stroke={colour} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          </svg>
        </div>
      )}
    </div>
  );
}

/** "Make something new": one tile per kind. A kind that cannot be made yet shows why and does nothing;
 * a design system can be made two ways, so its tile asks which. */
export function NewTiles({ onMake }: { onMake: (kind: PageKind, describe?: boolean) => void }) {
  const [asking, setAsking] = useState(false);
  const askRef = useRef<HTMLDivElement>(null);
  useClickOutside(askRef, () => setAsking(false), asking);
  const choice = "flex w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--card-bg)]";
  return (
    <section aria-label="Make something new">
      <h2 className="text-sm text-[var(--muted)]">Make something new</h2>
      <div className="mt-3 flex flex-wrap gap-4">
        {PAGE_ORDER.map((kind) => {
          const info = PAGE_KINDS[kind];
          const asks = kind === "design-system";
          return (
            <div key={kind} className="relative" ref={asks ? askRef : undefined}>
              <button
                type="button"
                disabled={info.badge === "Soon"}
                aria-haspopup={asks ? "menu" : undefined}
                aria-expanded={asks ? asking : undefined}
                className="group w-[170px] text-left disabled:cursor-default"
                onClick={() => (asks ? setAsking((open) => !open) : onMake(kind))}
              >
                <span className="block rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-1 shadow-sm transition-colors group-enabled:group-hover:border-[var(--border-hover)] group-disabled:opacity-60">
                  <span className="block overflow-hidden rounded-xl">
                    <Illustration kind={kind} />
                  </span>
                </span>
                <span className="mt-2 flex items-center gap-2 px-0.5">
                  <span className="font-medium">{info.label}</span>
                  {info.badge && <span className="rounded-md bg-[var(--card-bg)] px-1.5 py-0.5 text-xs font-medium text-[var(--muted)]">{info.badge}</span>}
                </span>
              </button>
              {asks && asking && (
                <div role="menu" className="absolute left-0 top-full z-20 mt-1 w-56 rounded-[14px] border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 shadow-[var(--shadow)]">
                  <button type="button" role="menuitem" className={choice} onClick={() => { setAsking(false); onMake(kind); }}>
                    Blank form
                  </button>
                  <button type="button" role="menuitem" className={choice} onClick={() => { setAsking(false); onMake(kind, true); }}>
                    Describe it
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
