import type { SVGProps } from "react";
import type { PageKind } from "../../lib/artifacts";

function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...props}>
      {children}
    </svg>
  );
}

/** The sidebar's entry: shapes of different kinds, for the different things coscribe makes. */
export function ArtifactsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <circle cx="7.5" cy="16.5" r="3.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
      <path d="M7.5 3.5 11 9.5H4Z" />
      <path d="M15 4h5" />
      <path d="M15 8h5" />
    </Icon>
  );
}

export function PinIcon({ filled, ...props }: SVGProps<SVGSVGElement> & { filled?: boolean }) {
  return (
    <Icon {...props} fill={filled ? "currentColor" : "none"}>
      <path d="M12 17v5" />
      <path d="M9 3h6l-1 6 3 3v2H7v-2l3-3Z" />
    </Icon>
  );
}

export function ListViewIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M9 6h11" />
      <path d="M9 12h11" />
      <path d="M9 18h11" />
      <path d="M4 6h.01" />
      <path d="M4 12h.01" />
      <path d="M4 18h.01" />
    </Icon>
  );
}

export function GridViewIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <rect x="4" y="4" width="6.5" height="6.5" rx="1.5" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5" />
    </Icon>
  );
}

const KIND_ICONS: Record<PageKind, (props: SVGProps<SVGSVGElement>) => React.JSX.Element> = {
  slides: (props) => (
    <Icon {...props}>
      <rect x="8" y="4" width="13" height="10" rx="2" />
      <path d="M5 8H4.5A1.5 1.5 0 0 0 3 9.5V17a2 2 0 0 0 2 2h9a1.5 1.5 0 0 0 1.5-1.5V17" />
    </Icon>
  ),
  docs: (props) => (
    <Icon {...props}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </Icon>
  ),
  sheets: (props) => (
    <Icon {...props}>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M4 10h16" />
      <path d="M4 15h16" />
      <path d="M10 10v10" />
    </Icon>
  ),
  design: (props) => (
    <Icon {...props}>
      <path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.8-.8 1.8-1.7 0-.5-.2-.9-.5-1.2-.3-.4-.5-.8-.5-1.3 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4C21 6.6 17 3 12 3Z" />
      <path d="M7.5 11h.01" />
      <path d="M10 7.5h.01" />
      <path d="M14.5 7.5h.01" />
    </Icon>
  ),
  dashboard: (props) => (
    <Icon {...props}>
      <path d="M4 4v16h16" />
      <path d="m8 15 3-4 3 2 5-6" />
    </Icon>
  ),
  "design-system": (props) => (
    <Icon {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="8" cy="12" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="16" cy="12" r="1.6" />
    </Icon>
  ),
};

export function KindIcon({ kind, ...props }: SVGProps<SVGSVGElement> & { kind: PageKind }) {
  return KIND_ICONS[kind](props);
}
