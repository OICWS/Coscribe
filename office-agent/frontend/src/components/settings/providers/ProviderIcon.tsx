import { LogoTile, type LogoSize } from "../LogoTile";

// The provider's own mark, bundled so the page doesn't depend on the network;
// the file is named after the provider's catalog name. A custom provider gets its first letter.
const ICONS = import.meta.glob("../../../assets/providers/*.{png,svg}", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

const BY_NAME = Object.fromEntries(
  Object.entries(ICONS).map(([path, url]) => [path.split("/").pop()!.replace(/\.\w+$/, ""), url]),
);

export function ProviderIcon({ name, title, size = "sm" }: { name: string; title: string; size?: LogoSize }) {
  return <LogoTile url={BY_NAME[name.toLowerCase()]} title={title} size={size} />;
}
