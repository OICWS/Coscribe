# Built-in plugins: PPTX Pages brings its build tool (shipped)

Why: step 5 of #1036 (decision 0058). A built-in plugin can bring a tool of the app, which a
plugin from elsewhere cannot; switching it off must take that tool away without changing the
fixed, provider-cached tool list (decision 0001).

## Shipped
- `builtin_skills/pptx-pages/` has a Claude plugin manifest (`"skills": "./"`, so the folder is
  its one skill) whose `coscribe.tools` names `build_pptx_from_pages`. `SkillInfo.builtin_tools()`
  reads it only for a plugin shipped with Coscribe; `plugin_info()` returns it as `tools`.
- `capability_guard.py`: `held_plugin_tools` (the tools of a built-in plugin none of whose skills
  is on), `plugin_refusal`, `hold_to_plugins`. Where tools are deferred, a held tool is left out
  of what `search_tools`/`use_tool` reach; where every tool is bound (DeepSeek) and in
  sub-agents, it keeps its schema and refuses with a message that points to Settings › Plugins.
  `approvals.py` refuses it before any approval card.
- Settings › Plugins: a built-in plugin has no Remove, and its page names the tools it brings.
- Checked with DeepSeek, the plugin off: the tool refused with the plugin message and the model
  built the deck with the other slide tools.

## Not verified
- On Windows; the Plugins page change in the desktop app.
- The coordinator's prompt still names `build_pptx_from_pages`; with the plugin off, the
  refusal is what tells the model.

## Follow-ups
- Steps 6 and 7 of #1036: `load_skill` pointing to the connector tools; export as a `.zip`.
