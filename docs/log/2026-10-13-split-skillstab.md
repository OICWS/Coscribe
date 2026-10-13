# SkillsTab split into settings/skills/ (shipped)

Why: `office-agent/frontend/src/components/settings/SkillsTab.tsx` was 1,120 lines holding ten sub-views and their helpers (#167, part 2 of 3).

## Shipped
- `components/settings/SkillsTab.tsx` (now 265 lines) keeps its name and export and is the composition: state, the actions, the list and Discover.
- `components/settings/skills/` holds one file per sub-view (`SkillRow`, `SkillMenu`, `SkillDetailView`, `PluginCard`, `PluginDetailView`, `UploadSkillView`, `FileTree`, `FileViewer`, `badges`) and the pieces without JSX: `helpers.ts`, `types.ts`.
- Moves only. A check of the multiset of lines before and after shows only imports, `export` keywords and the relative path of the lazy `Markdown` import changed.
- `helpers.test.ts` (13 tests, vitest) for the pure helpers that had none: file extension, short date, search matching, file tree, front-matter stripping, connector titles. Each assertion was checked by breaking the line it protects.
- Eleven views (list, a row's menu, a skill's page, the Add menu, Upload, Discover, a plugin's Overview, Contents, Skills and Connectors tabs) rendered before and after at 1280x860 are pixel-identical.
- All 15 Playwright specs of the nightly E2E list pass against the stub model on the branch, run locally.

## Not verified
- The desktop app on Windows (the maintainer looks).

## Follow-ups
- `ChatLog` is part 3 of #167.
