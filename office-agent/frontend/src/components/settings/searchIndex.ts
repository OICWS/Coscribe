import { GENERAL_FIELDS } from "./fields";
import type { SettingsCategory } from "./SettingsModal";

export interface SettingEntry {
  category: SettingsCategory;
  /** Exactly the label the page's SettingRow shows; it is also how the row is found to scroll to. */
  label: string;
  /** Other words a person might type for it. */
  keywords?: string;
}

const fieldLabel = (fields: { key: string; label: string }[], key: string) => fields.find((f) => f.key === key)?.label ?? key;

// Tabs mount only while open, so their rows can't be read from the page: this
// lists them, and a row missing here is simply not searchable.
const SETTING_ENTRIES: SettingEntry[] = [
  { category: "general", label: "Theme", keywords: "dark light mode appearance" },
  { category: "general", label: "Interface font", keywords: "typeface appearance" },
  { category: "general", label: "Motion", keywords: "animation reduce appearance" },
  { category: "general", label: "What should Coscribe call you?", keywords: "name profile" },
  { category: "general", label: fieldLabel(GENERAL_FIELDS, "COSCRIBE_DEFAULT_MODEL") },
  { category: "general", label: "Default mode", keywords: "permission manual auto plan accept edits" },
  { category: "general", label: "Global instructions", keywords: "memory preferences" },
  { category: "general", label: "Keep running in the background", keywords: "tray close window" },
  { category: "general", label: "Notifications" },
  // Its address, bypass list, user name and password show only once a manual proxy is chosen, so
  // they are found through this row.
  { category: "general", label: "Proxy", keywords: "network internet address do not use for bypass user name password" },
  { category: "workspace", label: "Environments", keywords: "folder workspace internet access new edit" },
  { category: "workspace", label: "Other folders", keywords: "directory read write" },
  { category: "capabilities", label: "Run scripts", keywords: "python sandbox isolation" },
  { category: "capabilities", label: "Run commands", keywords: "shell terminal sandbox" },
  { category: "capabilities", label: "Command sandbox", keywords: "basic full administrator" },
  { category: "capabilities", label: "Private folders", keywords: "documents desktop downloads hide" },
  { category: "capabilities", label: "Allowed sites", keywords: "browser websites" },
  { category: "capabilities", label: "Chats can hand tasks to Code", keywords: "codex" },
  { category: "capabilities", label: "Model for code", keywords: "codex" },
  { category: "capabilities", label: "Change files without asking", keywords: "codex approval" },
  { category: "capabilities", label: "Python for scripts", keywords: "interpreter download" },
  { category: "capabilities", label: "Packages for scripts", keywords: "library pip npm node add" },
  { category: "capabilities", label: "LibreOffice", keywords: "page previews download layout" },
  { category: "capabilities", label: "Codex", keywords: "download update remove coding agent" },
  { category: "general", label: "Prompt suggestions", keywords: "autocomplete tab" },
  { category: "general", label: "Background agents" },
  { category: "general", label: "Archive inactive conversations", keywords: "days old" },
  { category: "general", label: "Draw attention when Coscribe needs you", keywords: "flash taskbar" },
  { category: "general", label: "Keep computer awake while Coscribe works", keywords: "sleep" },
  { category: "general", label: "Keep awake on battery power" },
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
