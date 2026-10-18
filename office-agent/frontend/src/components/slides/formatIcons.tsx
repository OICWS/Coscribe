import type { SVGProps } from "react";

const stroke = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

type Icon = SVGProps<SVGSVGElement>;

export const BoldIcon = (props: Icon) => (
  <svg {...stroke} strokeWidth={2.2} {...props}>
    <path d="M7 5h6a3.5 3.5 0 0 1 0 7H7zM7 12h7a3.5 3.5 0 0 1 0 7H7z" />
  </svg>
);

export const ItalicIcon = (props: Icon) => (
  <svg {...stroke} {...props}>
    <path d="M10 5h8M6 19h8M14 5l-4 14" />
  </svg>
);

export const UnderlineIcon = (props: Icon) => (
  <svg {...stroke} {...props}>
    <path d="M7 4v7a5 5 0 0 0 10 0V4M5 20h14" />
  </svg>
);

export const ListIcon = (props: Icon) => (
  <svg {...stroke} {...props}>
    <path d="M9 6h11M9 12h11M9 18h11" />
    <circle cx="4.5" cy="6" r="0.6" fill="currentColor" />
    <circle cx="4.5" cy="12" r="0.6" fill="currentColor" />
    <circle cx="4.5" cy="18" r="0.6" fill="currentColor" />
  </svg>
);

const ALIGN_LINES = {
  left: "M4 6h16M4 10h10M4 14h16M4 18h10",
  center: "M4 6h16M7 10h10M4 14h16M7 18h10",
  right: "M4 6h16M10 10h10M4 14h16M10 18h10",
};

export const AlignIcon = ({ align, ...props }: Icon & { align: keyof typeof ALIGN_LINES }) => (
  <svg {...stroke} {...props}>
    <path d={ALIGN_LINES[align]} />
  </svg>
);

export const CommentPlusIcon = (props: Icon) => (
  <svg {...stroke} {...props}>
    <path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4.2A8 8 0 1 1 20 11.5z" />
    <path d="M12 8.5v6M9 11.5h6" />
  </svg>
);
