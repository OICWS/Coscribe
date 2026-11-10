export interface SettingsField {
  key: string;
  label: string;
  placeholder: string;
  /** Shown under the label, SettingRow-style -- what this actually does
   * and its consequence, not a restatement of the label. The old
   * layout crammed this into the input's own placeholder text (see e.g.
   * Max Turns' old "20 (caps a single agent loop's tool-calling
   * turns)"), which meant it vanished the moment you typed a value. */
  description: string;
}

/** These key names are also what POST /api/config expects and what BLANK_UNSAFE_ENV_VARS
 * validates server-side (see coscribe/web/app.py). */
export const GENERAL_FIELDS: SettingsField[] = [
  {
    key: "COSCRIBE_DEFAULT_MODEL",
    label: "Default model",
    placeholder: "provider:model",
    description: "What a new conversation starts with. Each conversation can switch from its own model picker.",
  },
];

export const USER_NAME_KEY = "COSCRIBE_USER_NAME";

export const CODE_MODEL_KEY = "COSCRIBE_CODE_MODEL";
export const CODE_MODULE_ENABLED_KEY = "COSCRIBE_CODE_MODULE_ENABLED";

/** Absent means on; only "false" turns it off. */
export const PROMPT_SUGGESTIONS_KEY = "COSCRIBE_PROMPT_SUGGESTIONS";

/** Absent means on; only "false" turns it off. */
export const BACKGROUND_AGENTS_KEY = "COSCRIBE_BACKGROUND_AGENTS";

/** Days of silence before a conversation is archived; absent or blank means never. */
export const ARCHIVE_INACTIVE_DAYS_KEY = "COSCRIBE_ARCHIVE_INACTIVE_DAYS";
export const ARCHIVE_INACTIVE_OPTIONS = [
  { value: "", label: "Never" },
  { value: "7", label: "After 7 days" },
  { value: "30", label: "After 30 days" },
  { value: "90", label: "After 90 days" },
] as const;

/** Desktop-shell-only, like NOTIFICATIONS_KEY; absent means on. */
export const FLASH_ON_ATTENTION_KEY = "COSCRIBE_FLASH_ON_ATTENTION";
export const KEEP_AWAKE_KEY = "COSCRIBE_KEEP_AWAKE";
export const KEEP_AWAKE_ON_BATTERY_KEY = "COSCRIBE_KEEP_AWAKE_ON_BATTERY";

export const PERMISSION_MODE_KEY = "COSCRIBE_DEFAULT_PERMISSION_MODE";
export const PERMISSION_MODES = [
  { value: "manual", label: "Manual" },
  { value: "accept-edits", label: "Accept Edits" },
  { value: "plan", label: "Plan" },
  { value: "auto", label: "Auto" },
] as const;

/** Desktop-shell-only toggle -- see ConfigResponse's own doc in
 * types/settings.ts and office-agent-desktop's lib.rs
 * (should_keep_running_in_background). Not in GENERAL_FIELDS: it's a
 * ToggleSwitch, not a text SettingsField, and deliberately excluded
 * from restart_required server-side (see web/app.py's
 * DESKTOP_ENV_VARS), unlike everything in that list. */
export const BACKGROUND_ON_CLOSE_KEY = "COSCRIBE_BACKGROUND_ON_CLOSE";

/** Desktop-shell-only, like BACKGROUND_ON_CLOSE_KEY: which finished task
 * runs get a notification. */
export const NOTIFICATIONS_KEY = "COSCRIBE_NOTIFICATIONS";
export const NOTIFICATION_LEVELS = [
  { value: "all", label: "All" },
  { value: "problems", label: "Problems only" },
  { value: "off", label: "Off" },
] as const;

const READABLE_DIRS_KEY = "COSCRIBE_EXTRA_READABLE_DIRS";
const WRITABLE_DIRS_KEY = "COSCRIBE_EXTRA_WRITABLE_DIRS";
const DELETABLE_DIRS_KEY = "COSCRIBE_EXTRA_DELETABLE_DIRS";

export type DirPermission = "read" | "read-write" | "read-write-delete";

/** The .env key each permission is stored under. */
const DIR_KEYS: Record<DirPermission, string> = {
  read: READABLE_DIRS_KEY,
  "read-write": WRITABLE_DIRS_KEY,
  "read-write-delete": DELETABLE_DIRS_KEY,
};

export interface DirEntry {
  path: string;
  permission: DirPermission;
}

type DirsConfig = Partial<Record<string, string | null>>;

function parseDirsList(value: string | null | undefined): string[] {
  return (value ?? "")
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}

/** The widest permission wins when a path is listed under several keys. */
export function buildDirEntries(config: DirsConfig): DirEntry[] {
  const entries = new Map<string, DirPermission>();
  for (const permission of Object.keys(DIR_KEYS) as DirPermission[]) {
    for (const path of parseDirsList(config[DIR_KEYS[permission]])) entries.set(path, permission);
  }
  return [...entries.entries()].map(([path, permission]) => ({ path, permission }));
}

/** The .env values that differ from `config`. Comma+space join must match
 * buildDirEntries' parse format or every settings-open shows a spurious diff. */
export function changedDirs(entries: DirEntry[], config: DirsConfig): Record<string, string> {
  const changed: Record<string, string> = {};
  for (const permission of Object.keys(DIR_KEYS) as DirPermission[]) {
    const key = DIR_KEYS[permission];
    // A deletable folder is listed as writable too: the server writes wherever it lists one.
    const value = entries
      .filter((e) => e.permission === permission || (permission === "read-write" && e.permission === "read-write-delete"))
      .map((e) => e.path)
      .join(", ");
    if (value !== (config[key] ?? "")) changed[key] = value;
  }
  return changed;
}
