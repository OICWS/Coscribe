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

/** Mirrors app.js's GENERAL_FIELDS/WORKSPACE_FIELDS exactly -- these key
 * names are also what POST /api/config expects and what BLANK_UNSAFE_ENV_VARS
 * validates server-side (see coscribe/web/app.py). */
export const GENERAL_FIELDS: SettingsField[] = [
  {
    key: "COSCRIBE_DEFAULT_MODEL",
    label: "Default model",
    placeholder: "provider:model",
    description:
      "What a new conversation starts with. Each conversation can switch from its own model picker.",
  },
  {
    key: "COSCRIBE_MAX_TURNS",
    label: "Max steps per reply",
    placeholder: "150",
    description:
      "The most model calls one reply can make before it stops, approvals included. Raise it if long tasks stop before they finish.",
  },
  {
    key: "COSCRIBE_REVIEWER_NAME",
    label: "Reviewer name",
    placeholder: "Your computer's user name",
    description:
      "The name on your replies and comments in a Word file's review panel. Empty uses your computer's user name, as Word does.",
  },
];

// Log Level's real values are this fixed, small set (Python's own logging
// module level names) -- rendered as a SegmentedControl instead of free
// text, see GeneralTab.tsx. Not in GENERAL_FIELDS above: that array feeds
// a generic free-text-field loop, and this isn't one.
export const USER_NAME_KEY = "COSCRIBE_USER_NAME";
export const USER_ROLE_KEY = "COSCRIBE_USER_ROLE";
export const USER_ROLES = [
  { value: "", label: "Not set" },
  { value: "Student", label: "Student" },
  { value: "Researcher", label: "Researcher" },
  { value: "Engineer", label: "Engineer" },
  { value: "Analyst", label: "Analyst" },
  { value: "Manager", label: "Manager" },
  { value: "Designer", label: "Designer" },
  { value: "Writer", label: "Writer" },
  { value: "Other", label: "Other" },
] as const;

export const LOG_LEVEL_KEY = "COSCRIBE_LOG_LEVEL";
export const LOG_LEVELS = [
  { value: "DEBUG", label: "Debug" },
  { value: "INFO", label: "Info" },
  { value: "WARNING", label: "Warning" },
  { value: "ERROR", label: "Error" },
] as const;

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

// Skills Directory is a real folder (unlike the file-path fields below it in
// this array), so it's the one WORKSPACE_FIELDS entry GeneralTab/WorkspaceTab
// pairs with a DirBrowserModal "Browse..." button -- see WorkspaceTab.tsx.
export const SKILLS_DIR_KEY = "COSCRIBE_SKILLS_DIR";

export const WORKSPACE_FIELDS: SettingsField[] = [
  {
    key: SKILLS_DIR_KEY,
    label: "Skills folder",
    placeholder: "./skills",
    description: "Where your own skills are kept, alongside the built-in ones.",
  },
  {
    key: "COSCRIBE_MEMORY_PATH",
    label: "Memory file",
    placeholder: "./MEMORY.md",
    description: "Where your global instructions are kept.",
  },
  {
    key: "COSCRIBE_MCP_CONFIG_PATH",
    label: "Connectors config file",
    placeholder: "(none)",
    description: "An MCP server config file loaded alongside the Connectors page.",
  },
  {
    key: "COSCRIBE_PROVIDERS_CONFIG_PATH",
    label: "Providers config file",
    placeholder: "(none)",
    description: "A custom-provider config file loaded alongside the Providers page.",
  },
  {
    key: "COSCRIBE_HOOKS_CONFIG_PATH",
    label: "Hooks config file",
    placeholder: "(none)",
    description: "Commands that run on tool calls and other conversation events.",
  },
];

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

export const WORKSPACE_ROOT_KEY = "COSCRIBE_WORKSPACE_ROOT";
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
