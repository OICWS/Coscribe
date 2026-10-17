import type { SVGProps } from "react";

const stroke = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

/** A window in front of another: open in a window of its own. */
export function NewWindowIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...stroke} {...props}>
      <rect x="8" y="8" width="12" height="12" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </svg>
  );
}

/** An arrow into the corner of a frame: back into the main window. */
export function DockBackIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...stroke} {...props}>
      <path d="M13 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5" />
      <path d="M4 4l8 8" />
      <path d="M12 6v6H6" />
    </svg>
  );
}

export function PinIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...stroke} {...props}>
      <path d="M12 17v5" />
      <path d="M9 3h6l-1 6 3 3v2H7v-2l3-3-1-6z" />
    </svg>
  );
}
