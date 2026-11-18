import { LogoTile, type LogoSize } from "./LogoTile";

// Each service's own app icon, bundled so the page doesn't depend on the
// network. A connector without one (a custom server) gets its first letter.
const ICONS = import.meta.glob("../../assets/connectors/*.{png,jpg,svg}", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

// Names a plugin's connector list uses that differ from the icon's file.
const ALIASES: Record<string, string> = {
  "google calendar": "google-calendar",
  "google drive": "google-drive",
  "microsoft-365": "m365",
  "amplitude-eu": "amplitude",
  "otter-ai": "otter",
};

function iconUrl(rawName: string): string | undefined {
  const name = ALIASES[rawName] ?? rawName;
  for (const [path, url] of Object.entries(ICONS)) {
    if (path.split("/").pop()?.replace(/\.\w+$/, "") === name) return url;
  }
  return undefined;
}

export function ConnectorIcon({ name, title, size = "sm" }: { name: string; title: string; size?: LogoSize }) {
  return <LogoTile url={iconUrl(name)} title={title} size={size} />;
}
