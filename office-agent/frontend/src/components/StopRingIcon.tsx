import type { SVGProps } from "react";

/** A ring with a dot: the Stop button while a reply is being worked on. It is the size of the context
 * ring beside it, so the two line up. */
export function StopRingIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="12" r="4" fill="currentColor" />
    </svg>
  );
}
