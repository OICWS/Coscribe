import { useEffect, useState } from "react";
import { getSlideDeck, slideImageUrl, type SlideDeck } from "../../lib/slides";

export default function PresentationPreview({ threadId, path, revision }: { threadId: string; path: string; revision: string }) {
  const [deck, setDeck] = useState<SlideDeck>();
  const [error, setError] = useState("");
  const [index, setIndex] = useState(0);
  useEffect(() => {
    let active = true;
    void getSlideDeck(threadId, path).then(
      (result) => { if (active) { setDeck(result); setError(""); } },
      () => { if (active) setError("This presentation could not be previewed."); },
    );
    return () => { active = false; };
  }, [threadId, path, revision]);
  const count = deck?.slides.length ?? 0;
  const current = Math.min(index, count - 1);
  if (error || !count) return <p className="p-4 text-sm text-[var(--muted)]">
    {error || (deck ? "This presentation has no slides." : "Loading slides…")}
  </p>;
  return <div className="flex h-full min-h-0 flex-col">
    <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4">
      <img src={slideImageUrl(threadId, path, current, revision)} alt={`Slide ${current + 1}`} className="max-h-full max-w-full object-contain" />
    </div>
    <div className="flex shrink-0 items-center justify-center gap-4 border-t border-[var(--border)] p-2 text-sm">
      <button type="button" className="rounded border border-[var(--border)] px-2 py-1 disabled:opacity-40" disabled={current === 0} onClick={() => setIndex(current - 1)}>Previous</button>
      <span aria-live="polite">Slide {current + 1} of {count}</span>
      <button type="button" className="rounded border border-[var(--border)] px-2 py-1 disabled:opacity-40" disabled={current === count - 1} onClick={() => setIndex(current + 1)}>Next</button>
    </div>
  </div>;
}
