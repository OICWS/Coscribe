import type { StepRecord, TaskMemoryValues, Workflow } from "./workflow";

/**
 * REST request/response shapes for the settings panel, hand-encoded from
 * coscribe/web/app.py the same way types/wire.ts encodes the WS
 * contract. Field names/optionality match the backend's actual dict
 * shapes exactly (see that file's endpoint handlers), not app.js's
 * assumptions about them.
 */

// ---------------------------------------------------------------------
// Config (General + Workspace tabs)
// ---------------------------------------------------------------------

export interface MaskedKey {
  set: boolean;
  masked: string | null;
}

export interface ConfigResponse {
  ANTHROPIC_API_KEY: MaskedKey;
  OPENAI_API_KEY: MaskedKey;
  GEMINI_API_KEY: MaskedKey;
  COSCRIBE_ANTHROPIC_DEFAULT_MODEL: string | null;
  COSCRIBE_OPENAI_DEFAULT_MODEL: string | null;
  COSCRIBE_GEMINI_DEFAULT_MODEL: string | null;
  COSCRIBE_DEFAULT_MODEL: string | null;
  COSCRIBE_WORKSPACE_ROOT: string | null;
  COSCRIBE_SKILLS_DIR: string | null;
  COSCRIBE_MEMORY_PATH: string | null;
  COSCRIBE_MCP_CONFIG_PATH: string | null;
  COSCRIBE_PROVIDERS_CONFIG_PATH: string | null;
  COSCRIBE_HOOKS_CONFIG_PATH: string | null;
  COSCRIBE_LOG_LEVEL: string | null;
  COSCRIBE_EXTRA_READABLE_DIRS: string | null;
  COSCRIBE_EXTRA_WRITABLE_DIRS: string | null;
  COSCRIBE_EXTRA_DELETABLE_DIRS: string | null;
  COSCRIBE_MAX_TURNS: string | null;
  COSCRIBE_CODE_MODEL: string | null;
  COSCRIBE_SIDE_MODEL: string | null;
  COSCRIBE_CODE_MODULE_ENABLED: string | null;
  COSCRIBE_PROMPT_SUGGESTIONS: string | null;
  COSCRIBE_BACKGROUND_AGENTS: string | null;
  COSCRIBE_ARCHIVE_INACTIVE_DAYS: string | null;
  COSCRIBE_WEBHOOK_PORT: string | null;
  COSCRIBE_FLASH_ON_ATTENTION: string | null;
  COSCRIBE_KEEP_AWAKE: string | null;
  COSCRIBE_KEEP_AWAKE_ON_BATTERY: string | null;
  COSCRIBE_USER_NAME: string | null;
  COSCRIBE_USER_ROLE: string | null;
  /** Desktop-shell-only, Rust-consumed (see office-agent-desktop's
   * lib.rs) -- "false" opts out of the default hide-on-close/keep-
   * running-in-background behavior. Absent/null/anything but exactly
   * "false" means the default (keep running) is in effect. No-op in
   * browser mode, where there's no window to hide in the first place. */
  COSCRIBE_BACKGROUND_ON_CLOSE: string | null;
}

// ---------------------------------------------------------------------
// Memory (Global instructions editor, General tab)
// ---------------------------------------------------------------------

export interface MemoryResponse {
  content: string;
}

export interface ConfigUpdateResult {
  restart_required: boolean;
  rejected: Record<string, string>;
}

export interface BrowseDirsEntry {
  name: string;
  path: string;
}

export type BrowseDirsResponse =
  | { error: string }
  | { path: string; parent: string | null; directories: BrowseDirsEntry[] };

// ---------------------------------------------------------------------
// Tools tab
// ---------------------------------------------------------------------

export interface ToolParam {
  name: string;
  /** Coarse, for picking an input control; "other" = a list or object. */
  type: "text" | "number" | "boolean" | "other";
  required: boolean;
  default: string | number | boolean | null;
  description: string;
}

export interface ToolInfo {
  name: string;
  category: string;
  risk_category: "READ" | "WRITE_LOCAL" | "EXEC" | "EXTERNAL";
  requires_approval: boolean;
  description: string;
  params: ToolParam[];
  /** A connector's tool: its connector marks it read-only. */
  read_only?: boolean;
}

export interface ToolsResponse {
  tools: ToolInfo[];
}

// ---------------------------------------------------------------------
// Skills tab
// ---------------------------------------------------------------------

export interface SkillInfo {
  name: string;
  description: string;
  /** builtin: ships with coscribe; anthropic: added from Discover; custom: yours. */
  source: "builtin" | "anthropic" | "custom";
  enabled: boolean;
  /** When its SKILL.md last changed, ISO 8601. */
  updated: string;
}

export interface SkillPlugin {
  id: string;
  title: string;
  author: string;
  repo: string;
  version: string;
  description: string;
  license: string;
  /** ISO date of the pinned commit. */
  updated: string;
  skills: string[];
  /** How many of `skills` are already added. */
  added: number;
}

export interface SkillPluginDetail extends SkillPlugin {
  files: string[];
  skill_details: { name: string; description: string }[];
  /** `connector` is coscribe's connector for the same server, if it has one. */
  connectors: { name: string; url: string; connector: string | null }[];
}

export type SkillsResponse = SkillInfo[];

export type UploadSkillResult = Pick<SkillInfo, "name" | "description"> | { error: string };

/** GET /api/skills/{name}/files -- flat, relative posix paths under that
 * skill's own real directory (a skill is a folder: SKILL.md plus
 * whatever reference docs/scripts it needs). The frontend folds this
 * into a tree client-side, see SkillsTab.tsx's buildFileTree. */
export interface SkillFilesResponse {
  files: string[];
}

/** GET /api/skills/{name}/files/{path} -- one file's raw text content
 * for the Skills tab's own preview pane. `error` covers every rejection
 * shape that endpoint can return (missing file, path traversal, binary
 * content, too large) -- one discriminated field, not a different HTTP
 * status per case the frontend has to branch on separately. */
export type SkillFileContentResult = { path: string; content: string } | { error: string };

// ---------------------------------------------------------------------
// Connectors tab (MCP)
// ---------------------------------------------------------------------

export interface McpSetupStep {
  title: string;
  body: string;
  link?: { label: string; url: string };
  /** Text to copy as it is: a command, a list of scopes. */
  copy?: { label: string; value: string }[];
  /** Show the redirect address to copy at this step. */
  redirect?: boolean;
}

/** What a service needs before it can be signed in to: an app its user (or organization) registers with it once. */
export interface McpSetup {
  /** Several connectors of one maker share one app. */
  group: string;
  provider: string;
  needs_secret: boolean;
  scopes?: string[];
  steps: McpSetupStep[];
  notes?: string;
}

export interface McpOAuthApps {
  saved: string[];
  redirect_uri: string;
}

export interface McpCatalogEntry {
  name: string;
  /** What people call it, e.g. "Microsoft 365"; `name` is its config key. */
  title?: string;
  description: string;
  /** A local server: the command that starts it. */
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  needs_config?: boolean;
  /** A hosted server, signed in to in the browser (`auth` is "oauth"). */
  server_url?: string;
  auth?: "oauth";
  setup?: McpSetup;
  made_by?: string;
  homepage?: string;
  category?: string;
  /** What it does, in a few sentences, for its own page. */
  about?: string;
  /** Tool names from the vendor's docs; the connected page lists the live ones. */
  tools?: string[];
  /** Where `tools` comes from: the service itself (reported when connected) or the maker's documentation. */
  tools_from?: "service" | "docs";
  links?: { label: string; url: string }[];
}

export type ConnectorToolPolicy = "allow" | "ask" | "block";

export interface ConnectorTool {
  name: string;
  title: string;
  description: string;
  read_only: boolean;
  policy: ConnectorToolPolicy;
}

export interface McpServerInfo {
  command?: string;
  args?: string[];
  masked_env?: Record<string, string>;
  /** Present instead of command/args/masked_env for a remote
   * (streamable_http) entry, e.g. a hand-configured Custom-tab server. */
  server_url?: string;
  masked_headers?: Record<string, string>;
  /** "oauth": signed in through the server's own page, no token to paste. */
  auth?: "oauth";
  /** Set while a sign-in is waiting for the user in their browser. */
  signin?: { url: string } | null;
  /** Why the last sign-in didn't work. */
  signin_error?: string | null;
  /** Why a secret this connector refers to can't be filled in (missing, or
   * not allowed for its host); the connector isn't started until it is. */
  secret_error?: string | null;
  /** Live signal, not derived from the static config the rest of this
   * entry comes from -- whether this server is currently connected in
   * the running coscribe-web process (see web/app.py's mcp_connections). */
  connected: boolean;
  /** A connected server's tools, blocked ones included. */
  tools?: ConnectorTool[];
}

export type McpServersResponse = Record<string, McpServerInfo>;

export interface McpServerUpdateResult {
  rejected: Record<string, string>;
  connected: boolean;
  /** Human-readable reason a connect attempt failed, or null on success
   * or when `rejected` already explains the outcome (a local validation
   * failure, caught before any connect was attempted). */
  error: string | null;
  /** A sign-in is waiting for the user in their browser. */
  signin?: { url: string };
}

export type NpmLatestVersionResponse = { package: string; latest: string } | { error: string };

// Both bump-version and reconnect return this same shape -- backend's
// web/app.py builds both from the same {"connected": ..., "error": ...}
// pattern (error non-null covers a thrown validate_mcp_config failure or
// "not found" too, not just a failed connect attempt).
export type McpVersionBumpResult = { connected: boolean; error: string | null };
export type McpReconnectResult = {
  connected: boolean;
  error: string | null;
  signin?: { url: string };
};

// ---------------------------------------------------------------------
// Providers tab
// ---------------------------------------------------------------------

export interface ProviderCatalogEntry {
  name: string;
  description: string;
  base_url: string;
  default_model: string;
  builtin: boolean;
}

export interface ProviderInfo {
  base_url: string | null;
  default_model: string;
  masked_key: string | null;
  builtin: boolean;
}

export type ProvidersResponse = Record<string, ProviderInfo>;

export interface ProviderUpdateResult {
  restart_required: boolean;
  rejected: Record<string, string>;
}

export interface ProviderDeleteResult {
  restart_required: boolean;
}

// ---------------------------------------------------------------------
// Environment tab (script-env packages for run_python_script)
// ---------------------------------------------------------------------

export interface ScriptEnvPackage {
  name: string;
  version: string;
}

export interface ScriptEnvInstallResult {
  success: boolean;
  error: string | null;
}

export interface FoundPython {
  path: string;
  version: string;
}

export interface ScriptEnvInterpreterInfo {
  /** The interpreter the person chose, or null: the first one found is used. */
  configured: string | null;
  /** Every Python 3 on this computer that runs, coscribe's own first once downloaded. */
  found: FoundPython[];
  /** coscribe's own Python, downloaded only when the person asks for it. */
  own_python: { available: boolean; version: string; downloaded: boolean };
}

export interface OwnPythonDownload {
  success: boolean;
  error: string | null;
  path?: string;
}

// ---------------------------------------------------------------------
// Scheduled Tasks tab
// ---------------------------------------------------------------------

// "once" predates the six-value Manual/Hourly/Daily/Weekdays/Weekly/Monthly
// frequency picker the Edit/Create modal offers -- kept in the union so an
// already-created "once" trigger's schedule still type-checks, but the
// modal never lets you pick it for a new/edited task.
export type ScheduleKind =
  | "manual"
  | "once"
  | "hourly"
  | "daily"
  | "weekdays"
  | "weekly"
  | "monthly"
  | "every"
  | "folder"
  | "connector"
  | "webhook";

export type ApprovalMode = "manual" | "auto" | "skip";

export interface ScheduleRule {
  kind: ScheduleKind;
  at: string;
  weekday: number | null;
  day_of_month: number | null;
  start_date: string | null;
  /** "every": minutes apart, 5 to 1440 (decision 0034). */
  minutes?: number | null;
  /** "folder": each new file there matching `pattern` starts a run, its path the file input `input`. */
  folder?: string | null;
  pattern?: string;
  input?: string | null;
  /** "connector" (decision 0039): every `minutes`, `tool` is asked with `args`, and each new item in
   * its answer starts a run. `inputs_from`: input -> the item's field, "*" the whole item, "" the
   * input's default; an input not named takes the field named like it. A "webhook" task (decision
   * 0040) fills its inputs from each event the same way, within `per_hour`. */
  tool?: string | null;
  args?: Record<string, unknown>;
  inputs_from?: Record<string, string>;
  per_hour?: number;
  /** The person confirmed a tool its connector doesn't mark read-only. */
  trust_unmarked?: boolean;
}

/** What a connector task's latest check found, and the items that started no run. */
export interface ConnectorCheckState {
  last_check: { at: string; found: number; held: number; error: string | null } | null;
  missed: { at: string; item: string; reason: string }[];
}

/** A "webhook" task's latest event, its sample and the events that started no run (decision 0040). */
interface WebhookState {
  /** The next event is kept as the sample instead of starting a run. */
  waiting: boolean;
  sample: unknown;
  /** Each field of the sample that is a value, by its dotted path. */
  fields: Record<string, unknown>;
  last_event: { at: string; status: number; message: string } | null;
  missed: { at: string; item: string; reason: string }[];
}

/** GET /api/scheduled-tasks/{id}/webhook: where a program sends the task's events, and with what key. */
export interface WebhookInfo extends WebhookState {
  url: string;
  /** Null when the keychain lost it: only a new key helps. */
  key: string | null;
  /** False when the port is taken by another program; `error` says so. */
  listening: boolean;
  error: string | null;
}

/** POST /api/mcp/check: what a connector's tool answers now. */
export type ConnectorCheckResult =
  | {
      read_only: boolean;
      /** Null when the tool isn't marked read-only and the person hasn't confirmed it. */
      items: { title: string; item: unknown }[] | null;
      count?: number;
      /** Each field of the first items that is a value, by its dotted path, with an example. */
      fields?: Record<string, unknown>;
      error?: string;
    }
  | { error: string };

/** "waiting": a wait step paused the run until a time or a file (decision 0033). */
export type RunStatus = "running" | "completed" | "failed" | "needs_approval" | "waiting" | "stopped";

/** One execution of a task, in its own conversation (thread_id). */
export interface ScheduledRun {
  run_id: string;
  thread_id: string;
  started_at: string;
  /** "file": a new file in the task's folder started it (decision 0034); "connector": a new item in
   * a connector's answer (decision 0039); "webhook": an event a program sent (decision 0040). */
  source: "manual" | "scheduled" | "file" | "connector" | "webhook";
  status: RunStatus;
  finished_at: string | null;
  error: string | null;
  /** A workflow run's steps, in the order they first ran. Empty otherwise. */
  steps: StepRecord[];
  inputs: Record<string, unknown> | null;
  /** Where a browser workflow run failed: a file under /api/screenshots/. */
  screenshot?: string | null;
  /** What a completed workflow run wrote. */
  files?: { path: string; size: number; rows?: number; columns?: number }[];
  /** The conversation looking into this failed run. */
  investigation?: string | null;
  /** The sites the run opened. */
  sites?: string[];
  /** Waiting for the browser, which another run or test is using. */
  queued?: boolean;
  /** A check ended it with nothing to do: how many such runs in a row it stands for (decision 0034). */
  quiet?: number;
  /** The versions of its task it ran, usually one (decision 0035). */
  versions?: number[];
  /** Per step that ran another task ("<step>" or "<step>/<its step>"): that task and its definition
   * as the run found it. */
  called?: Record<string, CalledTask>;
  /** What started a "connector" run (the connector, its tool, the item's key and the item) or a
   * "webhook" run (the event, as `item`). */
  event?: { connector?: string; tool?: string; key?: string; item: unknown } | null;
}

export interface ScheduledTask {
  trigger_id: string;
  name: string;
  schedule: ScheduleRule;
  enabled: boolean;
  created_at: string;
  next_run_at: string | null;
  prompt: string;
  last_run_at: string | null;
  last_run_status: string | null;
  model: string | null;
  approval_mode: ApprovalMode;
  notes_enabled: boolean;
  /** Oldest first. */
  runs: ScheduledRun[];
  /** Set when the task runs fixed steps instead of `prompt`. */
  workflow: Workflow | null;
  /** The id of the environment runs use ("default" for Default). */
  environment?: string;
  /** Ids of the conversation drafts saved into this task. */
  drafts?: string[];
  /** The conversation the task was saved from. */
  source_thread?: string | null;
  /** A failed run starts a conversation that looks into it. */
  auto_investigate?: boolean;
  /** What its runs were allowed while they waited, beyond what the steps name. */
  permissions?: { folders?: string[]; sites?: string[] };
  /** Its workflow's version number (decision 0035). */
  version?: number;
  /** What a run of it gives a task that runs it: each name its top-level steps save. */
  results?: string[];
  /** A "connector" task's latest check (decision 0039). */
  connector_check?: ConnectorCheckState;
  /** A "webhook" task's latest event (decision 0040). */
  webhook?: WebhookState;
}

export interface CalledTask {
  task: string;
  name: string;
  version: number | null;
  workflow: Workflow;
}

/** One saved definition of a task's workflow (decision 0035). */
export interface TaskVersion {
  number: number;
  saved_at: string;
  how: "created" | "edited" | "conversation" | "restored" | "found";
  /** A restored one's source. */
  from?: number;
  workflow: Workflow;
}

export interface CreateScheduledTaskPayload {
  name: string;
  kind: ScheduleKind;
  at: string;
  prompt: string;
  weekday?: number;
  day_of_month?: number;
  start_date?: string;
  model?: string;
  approval_mode?: ApprovalMode;
  notes_enabled?: boolean;
  workflow?: Workflow | null;
  environment?: string;
  /** The conversation draft this task is saved from, and that conversation. */
  from_draft?: string;
  from_thread?: string;
  auto_investigate?: boolean;
  /** For an "every", "folder" or "connector" kind. */
  watch?: {
    minutes?: number;
    folder?: string;
    pattern?: string;
    input?: string;
    tool?: string;
    args?: Record<string, unknown>;
    inputs_from?: Record<string, string>;
    per_hour?: number;
    trust_unmarked?: boolean;
  };
}

export type ScheduledTaskResult = ScheduledTask | { error: string };

export type RunNowResult = { task: ScheduledTask; run: ScheduledRun } | { error: string };

export type TaskNotesResult = { notes: string } | { error: string };

export type TaskMemoryResult = { memory: TaskMemoryValues } | { error: string };

export type ScheduledTaskDeleteResult = { deleted: string } | { error: string };

// ---------------------------------------------------------------------
// The code module (Settings > Code)
// ---------------------------------------------------------------------

export interface CodeStatus {
  version: string;
  installed: boolean;
  /** Downloading, or setting up after a download. */
  preparing: boolean;
  /** 0..1 while downloading. */
  progress: number | null;
  /** Bytes on disk once downloaded; null where there's no build. */
  size: number | null;
  /** Versions an earlier pin left on disk; `sandbox` when the command sandbox was set up with it. */
  older: { version: string; size: number; sandbox: boolean }[];
  /** What a chat's code task runs on. */
  model: string;
  /** Why the code module can't use that model; null when it can. */
  model_problem: string | null;
}

/** Whether the code module's commands and file changes ask first. */
export type CodePolicy = "ask" | "allow";

export interface CodePermissions {
  run_code_command: CodePolicy;
  apply_code_change: CodePolicy;
}

/** A global secret: the value is never sent to the browser, only its name and where it may be sent. */
export interface SecretInfo {
  name: string;
  hosts: string[];
  created_at: string | null;
}

export interface SecretsResponse {
  /** False on a computer with no keychain: nothing can be saved there. */
  keychain: boolean;
  secrets: SecretInfo[];
}

/** One row of the design-system library. */
export interface DesignSystemSummary {
  id: string;
  name: string;
  /** Its first colors, #RRGGBB. */
  palette: string[];
  updated_at: string;
}

export interface DesignColor {
  name: string;
  value: string;
  note: string;
}

export interface DesignTextStyle {
  id: string;
  name: string;
  size: number;
  weight: number;
  line_height: number;
  letter_spacing: number;
}

export interface DesignNamedValue {
  name: string;
  value: string;
}

/** A logo, icon or picture kept with a design system, with a note on when to use it. */
export interface DesignAsset {
  id: string;
  file: string;
  name: string;
  kind: "logo" | "icon" | "picture";
  note: string;
  width: number | null;
  height: number | null;
}

/** A design system (decision 0020): what a deck made with it follows. */
export interface DesignSystem {
  id: string;
  name: string;
  overview: string;
  colors: DesignColor[];
  typography: { fonts: string[]; styles: DesignTextStyle[] };
  spacing: DesignNamedValue[];
  radius: DesignNamedValue[];
  /** Kept and changed through their own routes, not the form's save. */
  assets?: DesignAsset[];
  updated_at: string;
}

/** How far an environment's conversations may reach the internet. */
export interface NetworkAccess {
  mode: "none" | "limited" | "full";
  /** For limited: a domain covers its subdomains; "*" is every site. */
  domains: string[];
}

/** The optional LibreOffice (decision 0026): coscribe's own copy, one installed on the computer, or none. */
export interface LibreOfficeStatus {
  found: boolean;
  source: "own" | "system" | null;
  path: string | null;
  /** Null when it was found but did not report one. */
  version: string | null;
  /** What a download would be here; null where there is none to offer. */
  offer: { version: string; download_bytes: number; installed_bytes: number } | null;
  working: boolean;
  /** download, unpack, trim or check while working. */
  step: string;
  done: number;
  total: number;
  /** Why the last download failed, in words for the person; named apart from `error`, which is
   * what a failed request answers with. */
  problem: string;
}

export interface ScriptIsolation {
  state: "passed" | "failed" | "untested" | "unsupported" | "setup_failed";
  /** The check that differed, when failed. */
  failed: string;
  detail: string;
}

/** A named environment: where its conversations work and what they may reach. */
export interface EnvironmentFields {
  name: string;
  /** The main folder first; none means the default workspace. */
  folders: string[];
  network: NetworkAccess;
  /** The secrets its conversations may use in a web request. */
  secrets: string[];
  /** Plain values the model can read; scripts get them as environment variables. */
  variables: Record<string, string>;
  /** Narrow Settings › Capabilities: off here refuses scripts or commands in this environment. */
  scripts: boolean;
  commands: boolean;
  /** Run scripts without isolation where the isolation check failed. */
  unisolated: boolean;
}

export interface Environment extends EnvironmentFields {
  id: string;
  /** How many conversations chose it; Default's count leaves out the ones that never chose. */
  used_by: number;
  /** How many scheduled tasks run in it. */
  tasks: number;
}

/** What coscribe may run on this computer (Settings › Capabilities). */
export interface Capabilities {
  scripts: boolean;
  commands: boolean;
  /** The second confirmation: commands may run as the person where the sandbox isn't set up. */
  commands_without_sandbox: boolean;
  /** A sandboxed command can't read the person's private folders (#601). */
  commands_hide_private_folders: boolean;
}

/** Codex's Windows sandbox for commands (decision 0022). */
export type CommandSandboxMode = "elevated" | "unelevated";

export interface CommandSandbox {
  state: "ready" | "off" | "failed" | "unsupported" | "working";
  /** Why it failed; while working, the step: "download", "approve" or "check" setting up,
   * "release" or "uninstall" removing. */
  detail: string;
  /** The mode it is (or was last) set up in; absent off Windows. */
  mode?: CommandSandboxMode;
  /** 0..1 while Codex downloads. */
  progress?: number | null;
  /** Set when removing it failed. */
  error?: string;
  /** Where setting it up gets the sandbox: built into the app, or with the Codex download. */
  source?: "bundled" | "codex";
}

/** Where what Settings › Capabilities downloads lives. */
export interface CapabilityFolders {
  codex: string;
  python_packages: string;
  node_packages: string;
}
