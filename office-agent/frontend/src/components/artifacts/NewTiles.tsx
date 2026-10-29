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
        <div className="flex h-[68%] w-[72%] items-center justify-center rounded-lg border border-white bg-white shadow-sm">
          <svg viewBox="12 10 76 65" className="h-[80%]" fill="none" stroke={colour} strokeWidth="4.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M53 14C30 14 17 28 17 42c0 16 15 29 31 29 12 0 19-5 19-13 0-6 1-9 7-12 6-3 9-8 9-14 0-11-13-18-30-18Z" />
            <g fill={colour} stroke="none">
              <circle cx="45" cy="31" r="5.3" />
              <circle cx="61" cy="32.5" r="5.3" />
              <circle cx="34.5" cy="43.8" r="5.3" />
            </g>
          </svg>
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
        <div className="flex h-[68%] w-[72%] items-center gap-3 rounded-lg border border-white bg-white px-3 shadow-sm">
          <svg viewBox="0 0 40 40" className="h-[70%] shrink-0" aria-hidden>
            <circle cx="20" cy="20" r="14" fill="none" strokeWidth="7" stroke={`color-mix(in srgb, ${colour} 18%, white)`} />
            <circle cx="20" cy="20" r="14" fill="none" strokeWidth="7" stroke={colour} strokeDasharray="58 88" transform="rotate(-90 20 20)" />
          </svg>
          <div className="flex flex-1 flex-col gap-1.5">
            {bar("60%", true)}
            {bar("100%")}
            {bar("75%")}
          </div>
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
