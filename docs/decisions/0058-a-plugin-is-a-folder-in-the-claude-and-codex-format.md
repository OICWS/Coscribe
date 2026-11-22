# 0058: A plugin is a folder in the Claude and Codex format; the core is not a plugin

Status: proposed (2026-11-22, OICWS; the maintainer chose the Claude and Codex format in the
project thread). Adds to 0001, 0044 and 0046, which it does not change.

## Context
A skill and the connectors it works with are only combined in Discover's fixed bundles. Claude
and Codex converged on one format (checked 2026-11-22): a folder with an optional manifest,
`skills/<name>/SKILL.md`, an `.mcp.json` of servers, and a `marketplace.json` in a git repository
as a source; a folder holding only a `SKILL.md` loads as a one-skill plugin. DeepSeek Harness
makes the core itself plugins (npm code in-process, outside its sandbox, by its own SAFETY.md not
secure); Claude and Codex keep the host fixed.

## Decision
- **A plugin is a folder** in that format: `plugin.json` at `.claude-plugin/`, `.codex-plugin/`
  or the root (optional), `skills/`, `.mcp.json`, `commands/`. A folder with only a `SKILL.md`
  is a one-skill plugin, so every existing skill folder is one. Agents, hooks, LSP servers and
  plugin dependencies are read but not used, and the plugin's page says so.
- **Three sources of ability**: built-in tools, which only built-in plugins bring; a plugin's own
  scripts, run as any script is (0021, 0022, a missing package through 0057); and connectors.
- **Built-in plugins are installed by default** (Codex's installation policy, Claude's
  `defaultEnabled`). Coscribe's bundled skills become built-in plugins; a built-in plugin names
  the deferred tools it brings, and switched off, its skills are not offered and its tools are
  neither found nor run. The fixed tool list (0001) keeps its shape.
- **Connectors are never listed on a plugin.** The model finds and offers one with
  `find_connector` and `offer_connector` (0046) when a skill needs a service; `load_skill` says
  so in fixed words. A plugin's `.mcp.json` is a hint the model reads; no server in it is added
  or started by installing the plugin.
- **Sources are git repositories with a marketplace.json.** A few curated sources come with
  Coscribe, pinned to a commit and checked by SHA-256 as Discover's catalog is; the person can
  add a source by its address or upload a `.zip`/`.plugin`, which no one has reviewed, and the
  page says so. Settings › Skills becomes Settings › Plugins: a plugin page, and a page per skill.
- **The core is not a plugin**: the agent loop, approvals, the sandboxes, secrets and the folder
  rules stay in the code and cannot be replaced by an installed plugin.

## Consequences
- Claude and Codex plugins, a company's own repository and GitHub's open ones install as they are.
- A plugin's instructions and scripts are trusted as the person who installed it trusts them.
- A plugin's skills may name a script by `${CLAUDE_PLUGIN_ROOT}`; it is replaced by the folder.
- Discover's bundles with their connector lists go; a plugin can be exported as a `.zip`.
