import { GENERAL_FIELDS, WORKSPACE_FIELDS } from "./fields";
import type { SettingsCategory } from "./SettingsModal";

export interface SettingEntry {
  category: SettingsCategory;
  /** Exactly the label the page's SettingRow shows; it is also how the row is found to scroll to. */
  label: string;
  /** Other words a person might type for it. */
  keywords?: string;
}

const fieldLabel = (fields: { key: string; label: string }[], key: string) =>
  fields.find((f) => f.key === key)?.label ?? key;

// Tabs mount only while open, so their rows can't be read from the page: this
// lists them, and a row missing here is simply not searchable.
const SETTING_ENTRIES: SettingEntry[] = [
  { category: "general", label: "Theme", keywords: "dark light mode appearance" },
  { category: "general", label: "Interface font", keywords: "typeface appearance" },
  { category: "general", label: "Motion", keywords: "animation reduce appearance" },
  { category: "general", label: fieldLabel(GENERAL_FIELDS, "COSCRIBE_REVIEWER_NAME"), keywords: "review comments author" },
  { category: "general", label: fieldLabel(GENERAL_FIELDS, "COSCRIBE_DEFAULT_MODEL") },
  { category: "general", label: "Default mode", keywords: "permission manual auto plan accept edits" },
  { category: "general", label: fieldLabel(GENERAL_FIELDS, "COSCRIBE_MAX_TURNS"), keywords: "turns limit" },
  { category: "general", label: "Global instructions", keywords: "memory preferences" },
  { category: "general", label: "Keep running in the background", keywords: "tray close window" },
  { category: "general", label: "Notifications" },
  { category: "general", label: "Log level", keywords: "debug logging" },
  { category: "workspace", label: "Default workspace", keywords: "folder directory" },
  { category: "workspace", label: fieldLabel(WORKSPACE_FIELDS, "COSCRIBE_SKILLS_DIR") },
  { category: "workspace", label: fieldLabel(WORKSPACE_FIELDS, "COSCRIBE_MEMORY_PATH") },
  { category: "workspace", label: fieldLabel(WORKSPACE_FIELDS, "COSCRIBE_MCP_CONFIG_PATH"), keywords: "mcp" },
  { category: "workspace", label: fieldLabel(WORKSPACE_FIELDS, "COSCRIBE_PROVIDERS_CONFIG_PATH") },
  { category: "workspace", label: fieldLabel(WORKSPACE_FIELDS, "COSCRIBE_HOOKS_CONFIG_PATH") },
  { category: "capabilities", label: "Run scripts", keywords: "python sandbox isolation" },
  { category: "capabilities", label: "Run commands", keywords: "shell terminal sandbox" },
  { category: "capabilities", label: "Chats can hand tasks to Code", keywords: "codex" },
  { category: "capabilities", label: "Model for code", keywords: "codex" },
  { category: "capabilities", label: "Change files without asking", keywords: "codex approval" },
  { category: "sessions", label: "Prompt suggestions", keywords: "autocomplete tab" },
  { category: "sessions", label: "Background agents" },
  { category: "sessions", label: "Archive inactive conversations", keywords: "days old" },
  { category: "sessions", label: "Draw attention when Coscribe needs you", keywords: "flash taskbar" },
  { category: "sessions", label: "Keep computer awake while Coscribe works", keywords: "sleep" },
  { category: "sessions", label: "Keep awake on battery power" },
];

/** Where `query` first occurs in `text`, ignoring case; null when it doesn't. */
export function matchRange(text: string, query: string): [number, number] | null {
  const at = text.toLowerCase().indexOf(query.toLowerCase());
  return at < 0 ? null : [at, at + query.length];
}

export function findSettings(query: string, limit = 30): SettingEntry[] {
  const q = query.trim();
  if (!q) return [];
  return SETTING_ENTRIES.filter((e) => matchRange(e.label, q) || matchRange(e.keywords ?? "", q)).slice(0, limit);
}
