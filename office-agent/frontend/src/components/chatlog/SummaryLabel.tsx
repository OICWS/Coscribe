import { type SummaryParts } from "../../lib/transcriptGrouping";
import { ChevronRightIcon } from "../icons";

/** "verb ⟨object chip⟩". A failed call is red as a whole; an aggregated
 * clause shows only its "(N failed)" count in red. The running call's
 * object is plain text so the shimmer (clipped to the text) runs through
 * it too. */
export function SummaryLabel({ parts }: { parts: SummaryParts }) {
  if (parts.shimmer) {
    return (
      <>
        <span className="shimmer-text">
          {parts.verb}
          {parts.object && `${parts.glue ?? " "}${parts.object}`}
        </span>
        {parts.failedCount !== undefined && (
          <span className="ml-1 text-[var(--danger)]">({parts.failedCount} failed)</span>
        )}
      </>
    );
  }
  const label = (
    <>
      {parts.verb}
      {parts.object && (
        <>
          {parts.glue ?? " "}
          <span className="font-medium text-[var(--fg)]">{parts.object}</span>
        </>
      )}
      {parts.failedCount !== undefined && (
        <span className="ml-1 text-[var(--danger)]">({parts.failedCount} failed)</span>
      )}
    </>
  );
  return parts.failed ? <span className="text-[var(--danger)]">{label}</span> : label;
}

export function Disclosure({ open }: { open: boolean }) {
  return (
    <ChevronRightIcon
      aria-hidden="true"
      className={`h-3.5 w-3.5 shrink-0 transition-transform motion-reduce:transition-none ${open ? "rotate-90" : ""}`}
    />
  );
}
