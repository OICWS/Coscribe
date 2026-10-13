export type View = { kind: "list" } | { kind: "upload" } | { kind: "detail"; name: string } | { kind: "plugin"; id: string };
export type Tab = "yours" | "discover";
export type PluginTab = "overview" | "contents" | "skills" | "connectors";
