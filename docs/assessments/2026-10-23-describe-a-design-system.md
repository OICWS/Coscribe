# Design note: making a design system by describing it (2026-10-23)

Design before code: the change adds a tool, a conversation type and UI, and one choice (how the
model's answer reaches the library) shapes the rest. Status: **proposed**, waiting for the
maintainer's answers to the questions at the end. Decisions it rests on: 0001 (a fixed, cached tool
list), 0020 (design systems are a library the user keeps; a deck gets a copy).

## 摘要（中文）
- 现在做设计系统只有空白表单。要加第二条路:在 Artifacts 里点 **Design system**,选 **Describe it**,开一个对话,说品牌或想要的风格(也可以附品牌手册 PDF、logo、网页截图),模型问清缺的信息,然后把颜色、字体、文字样式、间距和圆角存进库。存好后它出现在 Artifacts 里,和手工做的一样。
- 办法:加**一个延迟工具** `save_design_system`(模型通过 `search_tools` 找到它,不进固定工具列表,不改系统提示词);对话的第一条消息带一段说明(和 Slides 的写法相同);对话末尾出现一张卡片,点开就是设置里的编辑页。
- 这涉及 `coordinator.py`(不变式路径),需要独立评审。请你决定的几件事在最后。

## What exists
- The library and its routes (`tools/design_systems.py`, `/api/design-systems`), Settings > Design systems with the blank form, the Slides chip's choice, the checker that warns of strays, and design systems as cards on the Artifacts page.
- A conversation started from the Artifacts page carries a bracketed note in its first message (`artifact_note` in `runtime_lg/messages.py`); it never goes in the system prompt or a tool schema (0001).
- Tools the model does not always need are deferred: it finds them with `search_tools` and calls them with `use_tool` (`runtime_lg/tool_deferral.py`).
- The store already checks everything it saves (`_clean`: names, `#RRGGBB` colors, number ranges, row limits) and raises `DesignSystemError` with a reason.

## Proposed
1. **Entry.** The "Design system" tile of "Make something new" opens a small menu: **Blank form** (today's behaviour) and **Describe it**. Settings > Design systems gets the same second path beside "New design system".
2. **The conversation.** Describe it starts a conversation with a chip "Design system" and the placeholder "Describe the brand or the look you want…". The first message carries a note: what the person wants made, to ask for what is missing (brand colors, fonts, tone, who it is for), to read what they attached (a brand guide PDF, a logo, a screenshot of their site, using the file and image tools; a script may sample colors from a picture), to propose the system in words before saving, and to save it with `save_design_system` when they agree. It is a note in the message, like every other kind's.
3. **The tool.** `save_design_system(name, overview, colors, fonts, text_styles, spacing, radius, system_id=None)`: without `system_id` it makes a system, with one it replaces that system's editable fields. It goes through the store's `_clean`, so a bad value comes back to the model as the store's own message to repair. It returns the id, the name and a one-line summary. Risk tier `WRITE_LOCAL` (it writes the library, in the app's data folder, not the workspace): a manual-mode approval card shows the system, Accept Edits lets it through.
   - It is **deferred**, not core: nothing changes in the bound list a provider has cached; its schema is added to `tests/tool_schemas.txt` once, as any new tool is.
4. **The result.** The conversation ends with a card for the saved system (as a finished deck has one) that opens Settings on it; the system is also a card on the Artifacts page. A later "make it warmer" in the same conversation calls the tool again with the id.
5. **What stays as it is.** The library is per user; a system is not tied to the conversation that made it; a deck made from it gets a copy (0020). Nothing here claims more than the code keeps: the model only writes values the store accepts.

## Size and pull requests
About 350 lines in two PRs: (1) the tool, its note, the store call, tests and the schema snapshot (about 150, `coordinator.py` lists the tool, an invariant path: independent review); (2) the chip kind, the tile's menu, the end-of-turn card and a Playwright spec on the stub model (about 200). Hot files: `coordinator.py` (invariant), `App.tsx` (a few lines).

## Not verified
- How models behave: whether the cheaper ones fill the text styles with sensible sizes, or leave the defaults. The checker's warnings will tell what a deck does with the result.
- Colors read from a picture are the model's estimate, not measured, unless it samples them with a script.

## Questions for the maintainer
1. **A tool, or a file?** A tool (recommended) saves in the library directly, with the approval card as the check. The alternative, the model writing a JSON file in the workspace that Settings imports, needs no tool but one more step for the person.
2. **The tile.** A menu with Blank form and Describe it (recommended), or the tile always opening the conversation and the blank form staying in Settings?
3. **Editing existing systems.** In the first version the tool can replace a system's fields when given its id (recommended, small), or only make new ones?
4. **Later, on the same path:** assets (logos), and making a system from an uploaded .pptx. Both fit the same conversation; not in this change.
