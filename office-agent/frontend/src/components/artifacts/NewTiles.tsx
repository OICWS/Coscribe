import { KIND_ORDER, KINDS, type ArtifactKind } from "../../lib/artifacts";
import { tinted } from "./ArtifactThumb";

/** A small drawing of each kind, on the kind's colour. */
function Illustration({ kind }: { kind: ArtifactKind }) {
  const colour = KINDS[kind].colour;
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
      {kind === "sheets" && (
        <div className="grid w-[66%] grid-cols-4 overflow-hidden rounded-lg border border-white bg-white shadow-sm">
          {Array.from({ length: 16 }, (_, i) => (
            <span key={i} className="h-3.5 border-b border-r border-[#e7e5e2]" style={i < 4 ? { background: `color-mix(in srgb, ${colour} 26%, white)` } : undefined} />
          ))}
        </div>
      )}
      {kind === "dashboard" && (
        <div className="flex h-[68%] w-[72%] items-end gap-2 rounded-lg border border-white bg-white px-3 pb-3 shadow-sm">
          {[40, 70, 100, 55].map((height, i) => (
            <span key={i} className="flex-1 rounded-sm" style={{ height: `${height}%`, background: `color-mix(in srgb, ${colour} ${i === 2 ? 70 : 32}%, white)` }} />
          ))}
        </div>
      )}
    </div>
  );
}

/** "Make something new": one tile per kind. A kind that cannot be made yet shows why and does nothing. */
export function NewTiles({ onMake }: { onMake: (kind: ArtifactKind) => void }) {
  return (
    <section aria-label="Make something new">
      <h2 className="text-sm text-[var(--muted)]">Make something new</h2>
      <div className="mt-3 flex flex-wrap gap-4">
        {KIND_ORDER.map((kind) => {
          const info = KINDS[kind];
          return (
            <button
              key={kind}
              type="button"
              disabled={info.starter === null}
              className="group w-[170px] text-left disabled:cursor-default"
              onClick={() => onMake(kind)}
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
          );
        })}
      </div>
    </section>
  );
}
