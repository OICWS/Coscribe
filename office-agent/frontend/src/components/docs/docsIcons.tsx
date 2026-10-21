import type { SVGProps } from "react";

function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...props}>
      {children}
    </svg>
  );
}

export function OrderedListIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M10 6h10" />
      <path d="M10 12h10" />
      <path d="M10 18h10" />
      <path d="M4 5.5 5.5 5v3.5" />
      <path d="M4 12.5a1.3 1.3 0 0 1 2.4.6c0 .8-1 1.2-2.4 2.4H6.6" />
      <path d="M4 17.6h2.4l-1.4 1.4a1.2 1.2 0 1 1-1 1.5" />
    </Icon>
  );
}

export function QuoteIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M5 6v12" />
      <path d="M10 8h9" />
      <path d="M10 12h9" />
      <path d="M10 16h6" />
    </Icon>
  );
}

export function TableIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M4 10h16" />
      <path d="M10 10v9" />
    </Icon>
  );
}

export function ImageIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" />
      <circle cx="9" cy="10" r="1.5" />
      <path d="m4 17 5-5 4 4 2.5-2.5L20 18" />
    </Icon>
  );
}
