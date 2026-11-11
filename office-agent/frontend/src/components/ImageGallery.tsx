import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { copyImage } from "../lib/copyImage";
import { ChevronRightIcon, CloseIcon } from "./icons";

interface GalleryImage {
  name: string;
  src: string;
}

const iconButton = "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--card-bg)] disabled:opacity-40 disabled:hover:bg-transparent";

/** Pictures the conversation made, one at a time and large, with the rest in a strip below.
 * Arrow keys step, Escape closes. */
export function ImageGallery({ images, start, onClose }: { images: GalleryImage[]; start: number; onClose: () => void }) {
  const [index, setIndex] = useState(start);
  const [copiedAt, setCopiedAt] = useState<number | null>(null);
  const count = images.length;
  const step = (by: number) => setIndex((i) => Math.min(count - 1, Math.max(0, i + by)));

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
      else if (event.key === "ArrowRight") setIndex((i) => Math.min(count - 1, i + 1));
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose, count]);

  const image = images[index];
  if (!image) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-label={image.name}
        className="flex max-h-full w-full max-w-[56rem] flex-col overflow-hidden rounded-3xl bg-[var(--panel-bg)] shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
        data-testid="image-gallery"
      >
        <div className="flex items-center gap-3 px-6 pb-3 pt-5">
          <h2 className="min-w-0 flex-1 truncate text-lg font-semibold" title={image.name}>
            {image.name}
          </h2>
          {count > 1 && (
            <span className="shrink-0 text-sm tabular-nums text-[var(--muted)]">
              {index + 1} of {count}
            </span>
          )}
          <button
            type="button"
            className="h-10 shrink-0 rounded-xl border border-[var(--border)] px-3 text-sm hover:bg-[var(--card-bg)]"
            onClick={() => copyImage(image.src).then(() => setCopiedAt(index), () => undefined)}
          >
            {copiedAt === index ? "Copied" : "Copy"}
          </button>
          <button type="button" aria-label="Close" autoFocus className={iconButton} onClick={onClose}>
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 items-center gap-3 px-4">
          {count > 1 && (
            <button type="button" aria-label="Previous picture" className={iconButton} disabled={index === 0} onClick={() => step(-1)}>
              <ChevronRightIcon className="h-5 w-5 rotate-180" />
            </button>
          )}
          <img src={image.src} alt={image.name} draggable={false} className="mx-auto max-h-[64vh] min-w-0 max-w-full flex-1 rounded-lg object-contain" />
          {count > 1 && (
            <button type="button" aria-label="Next picture" className={iconButton} disabled={index === count - 1} onClick={() => step(1)}>
              <ChevronRightIcon className="h-5 w-5" />
            </button>
          )}
        </div>
        {count > 1 ? (
          <div className="flex gap-2 overflow-x-auto px-6 pb-5 pt-4">
            {images.map((item, i) => (
              <button
                key={item.src}
                type="button"
                title={item.name}
                aria-current={i === index}
                className={`h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2 ${i === index ? "border-[var(--accent)]" : "border-transparent opacity-70 hover:opacity-100"}`}
                onClick={() => setIndex(i)}
              >
                <img src={item.src} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        ) : (
          <div className="pb-6" />
        )}
      </div>
    </div>,
    document.body,
  );
}
