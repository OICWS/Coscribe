# A Claude or Codex plugin folder loads its skills, and uploads as a whole (shipped)

Why: step 2 of #1036 (decision 0058): a plugin is a folder in the format Claude and Codex share,
so their plugins, a company's own and GitHub's open ones install as they are.

## Shipped
- `tools/skills.py`: a folder of the skills directory (or a workspace's `.coscribe/skills`) with
  a manifest at `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` or `plugin.json`, or a
  `skills/` folder and no `SKILL.md` of its own, is a plugin. Each `skills/<name>/SKILL.md` loads
  as a skill carrying the plugin's name; a manifest's `skills` paths are followed only inside the
  plugin; a skill whose name is taken is skipped. A lone `SKILL.md` folder loads as before.
- `load_skill` replaces `${CLAUDE_PLUGIN_ROOT}` with the plugin's folder; `read_skill_file`
  reaches the whole plugin (its shared scripts), not only the skill's folder.
- Upload takes `.plugin` too; an archive holding a plugin (top level or one folder down) is kept
  whole under its manifest's name, and refused when it has no skill.
- One skill of a plugin is not removed alone; `DELETE /api/skills/<plugin>?plugin=true` removes
  the plugin's folder, and Settings › Skills' Remove on such a skill asks to remove the plugin.
- Tried on real plugins: Anthropic's marketing and finance (`.claude-plugin`), OpenAI's figma and
  build-web-apps (`.codex-plugin`, `"skills": "./skills/"`): 34 skills, each under its plugin;
  figma uploaded as a `.plugin` archive loads its 12 skills.
- With DeepSeek (`deepseek-flash`, the CLI): a `.claude-plugin` plugin whose skill names its
  script by `${CLAUDE_PLUGIN_ROOT}`; the model loaded the skill, ran the script by the filled-in
  absolute path with run_python_script and reported its numbers (11 words, 9 distinct). On Linux,
  so the script ran as the user, not in the AppContainer.

## Not verified
- On Windows; in the app's Settings by hand (the list shows plugin skills as skills until step 3).

## Follow-ups
- Steps 3 to 7 of #1036. A plugin's `.mcp.json`, commands, agents and hooks are kept but unused.
