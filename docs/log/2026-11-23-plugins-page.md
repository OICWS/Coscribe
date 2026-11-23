# Settings › Plugins: a plugin is one row with its own page (shipped)

Why: step 3 of #1036 (decision 0058): with plugins loading, Settings lists plugins, not only
skills, and Discover stops listing connectors on a plugin.

## Shipped
- Settings › Skills is now Settings › Plugins. Your plugins lists a plugin as one row (its skill
  count, author, description); a lone skill keeps its row. Search finds a plugin by any of its
  skills.
- A plugin's page: author, version, description, its skills as chips (a switched-off one struck
  through), and the parts Coscribe reads but does not use (commands, agents, hooks, MCP servers,
  apps, LSP servers), saying the model offers Coscribe's own connector when a skill needs one.
  On/off and Remove act on the whole plugin.
- A plugin's skill page says "Part of <plugin>", goes back to the plugin, and has no Remove of
  its own.
- `GET /api/skills` gives each skill `plugin_info` (name, description, version, author, unused
  parts) from `SkillInfo.plugin_info()`.
- Discover's plugin page has no Connectors tab; its route no longer returns connectors.

## Not verified
- On Windows, and by hand in the desktop app; checked in Chromium with real plugins (Anthropic's
  marketing, OpenAI's figma) in light and dark.

## Follow-ups
- Steps 4 to 7 of #1036.
