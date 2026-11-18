export type LogoSize = "sm" | "md" | "lg";

/** A service's logo on a white tile, or its first letter when there is none. */
export function LogoTile({ url, title, size = "sm" }: { url: string | undefined; title: string; size?: LogoSize }) {
  const box = size === "lg" ? "h-16 w-16 rounded-2xl" : size === "md" ? "h-10 w-10 rounded-xl" : "h-7 w-7 rounded-lg";
  if (url) {
    // A bitmap app icon fills its tile; a vector mark has no padding of its own.
    return (
      <img
        src={url}
        alt=""
        className={`${box} shrink-0 border border-[var(--border)] bg-white ${url.includes(".svg") ? "object-contain p-[18%]" : "object-cover"}`}
      />
    );
  }
  const text = size === "lg" ? "text-2xl" : size === "md" ? "text-base" : "text-xs";
  return (
    <span
      className={`${box} ${text} flex shrink-0 items-center justify-center border border-[var(--border)] bg-[var(--field-bg)] font-medium text-[var(--muted)]`}
    >
      {title.slice(0, 1).toUpperCase()}
    </span>
  );
}
