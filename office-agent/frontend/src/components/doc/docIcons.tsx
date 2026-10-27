import type { SVGProps } from "react";

type Icon = SVGProps<SVGSVGElement>;

const Svg = ({ children, ...props }: Icon) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...props}>
    {children}
  </svg>
);

export const StrikeIcon = (props: Icon) => (
  <Svg {...props}>
    <path d="M4 12h16" />
    <path d="M16.5 7.5C16 5.8 14.3 5 12 5c-2.5 0-4.3 1.1-4.3 3 0 1.4.9 2.3 2.6 3" />
    <path d="M7.5 16.5C8 18.2 9.7 19 12 19c2.6 0 4.5-1.1 4.5-3 0-1-.4-1.7-1.2-2.2" />
  </Svg>
);

export const CodeInlineIcon = (props: Icon) => (
  <Svg {...props}>
    <path d="m9 8-4 4 4 4" />
    <path d="m15 8 4 4-4 4" />
  </Svg>
);

export const FontIcon = (props: Icon) => (
  <Svg {...props}>
    <path d="M20 4c-6 0-11 3-13 9l-1.5 4.5" />
    <path d="M9 14c3.5 1 7-1.5 8-6" />
    <path d="M4 20c1-1 2.5-2.5 3.5-3.5" />
  </Svg>
);

/** Two arrows toward each other: the page narrows; away from each other it widens. */
export const WidthIcon = ({ wide, ...props }: Icon & { wide: boolean }) => (
  <Svg {...props}>
    {wide ? (
      <>
        <path d="M3 12h6M6 9l-3 3 3 3" />
        <path d="M21 12h-6M18 9l3 3-3 3" />
      </>
    ) : (
      <>
        <path d="M3 12h6M6.5 9 9.5 12l-3 3" />
        <path d="M21 12h-6M17.5 9 14.5 12l3 3" />
      </>
    )}
  </Svg>
);

export const ChecklistIcon = (props: Icon) => (
  <Svg {...props}>
    <path d="m3.5 6 1.5 1.5L8 4.5" />
    <path d="M11 6h10" />
    <rect x="3.5" y="13" width="4.5" height="4.5" rx="1" />
    <path d="M11 15.5h10" />
  </Svg>
);
