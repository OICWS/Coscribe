# coscribe at 1M lines with AI-only development: assessment and plan

Reviewer: independent session, 2026-10-11, on `origin/main` @ `447670d`. Nothing in the
repository was changed. Every number below was measured with the scripts in the appendix
unless it says "guess" or "not verified".

## 中文摘要

- **结论**：当前约 5 万行 Python + 3 万行 TS 的规模下，项目的“地板”（CI、mypy strict、ruff、
  import-linter 5 条契约、1,858 个测试、PR 流程）对 AI 协作而言已经比多数同规模项目好；但离
  “100 万行、每次只读一小片”还差三件结构性的事：(1) **包没有公开接口**——跨包导入中 80%
  (165/205) 直接钻进子模块，`web.app` 的传递依赖覆盖了 126 个模块中的 118 个；(2) **没有任何
  会随代码一起失效的文档检查**——已删除的 6 个文件仍被 126 处引用（`web/session.py` 两天前才
  移走，就留下 72 处）；(3) **评审和“未验证项”没有留下记录**——66 个 PR 中 0 条评审意见、0 个
  GitHub review；8 个 PR 触及不变量路径，没有一个能证明独立评审做过、发现了什么；37 条日志里
  33 条写了“未验证”（共 46 项），无人跟踪。
- **测试质量**：抽样 26 个测试，约 20 个通过公开入口验证行为（不是复述实现），这是好消息。
  实测覆盖率很高（自有代码行覆盖 91.3%、分支 83.1%），但 CI 里不测量；对不变量模块
  `runtime/secret_store.py`（覆盖率 95%）做变异测试，得分只有 68%：`encoding="utf-8"` 被删掉
  不会被任何 Linux 测试发现（正是 Windows GBK 那类 bug），密钥最短 8 位的边界、两种编码形式
  的脱敏都没有测试钉住。“覆盖率高”不等于“能挡住重构”。
- **CI 提速**：实测 `pytest -n 4` 在 4 核机器上一次全过，1,856 个测试 3 分 50 秒（现在串行约 8–9 分钟）。
- **不可能只靠 AI 解决的**：需求/意图错误、无沙箱设计的安全性、真机（Windows PATH、编码、
  钥匙串）行为、30+ 连接器与模型 API 的厂商漂移、同一模型家族的相关盲点。最低人工投入：
  每周约 2 小时的真机冒烟 + 未验证清单分诊；不变量路径与决策记录由人批准；季度安全复审。
- **顺序**：先建“棘轮”（只许变好不许变差的基线）和度量，再补记录评审和未验证清单，再加
  契约/快照测试，最后才拆大文件（`presentations.py` 7,092 行、`session.py` 3,755 行、
  `create_app_lg` 731 行）。前 5 步都可以马上做，每步一个 PR。
- **需要维护者拍板**：仓库是否迁到 GitHub 组织（merge queue、团队 CODEOWNERS 只对组织可用）、
  是否引入第二个模型家族做评审、谁有权放松棘轮基线、是否给“结构冲刺”冻结功能 2–3 周、
  核心代码是否设规模上限。

---

## 0. What I checked, and corrections to the brief

| Claim in the brief | What I found |
|---|---|
| ~50k Python source | 49,646 lines, of which 5,690 are vendored (`_native_formula`, `_native_docx_tracks`, `providers/gemini_provider.py`); 43,956 own lines in 117 modules |
| 37k tests, ~1,700 tests | 36,515 lines; 1,698 test functions, 1,858 collected. Collection alone takes 65 s locally |
| 26k frontend, 4k desktop | 26,341 lines / 125 files; desktop 3,628 |
| CI runs tsc -b, vite, oxlint, ruff, mypy strict, lint-imports (5 contracts, 3 exceptions), pytest ~12 min | Correct (`scripts/check.sh`, `office-agent-ci.yml`). Measured CI wall time over the last 58 runs: median 9.5 min, p90 11.9 min. A separate `desktop` typecheck job exists but is not a required check |
| No CODEOWNERS | **Wrong**: `.github/CODEOWNERS` exists and lists the invariant paths, but the ruleset has `require_code_owner_review: false`, so it is informational |
| No frontend unit tests | Correct: no vitest/jest; 17 Playwright specs in `frontend/tests/e2e/`, not run in CI |
| Frontend TS not strict? (not claimed, but `tsconfig.app.json` has no `strict`) | Not a gap: TypeScript 6.0.3 is strict by default (verified with a probe file: implicit `any` and `null` errors fire with no flag), and `tsc --strict` on the app gives 0 errors |
| Independent review only for invariant paths | Correct as written, but there is **no trace that it happens**: 0 review comments and 0 GitHub reviews on all 66 PRs; PRs #26, #60, #63 say "needs an independent `/code-review`" and nothing records the result |
| Hot files cause conflicts | Plausible, partly measured: since 10-01 `web/app.py` changed in 30 commits, `web/session.py` 20, `App.tsx` 13, `coordinator.py` 11. PR #64 was closed because #63 had built the same backend in parallel: one fully duplicated piece of work out of 66 PRs. Squash merges hide conflict resolution, so I cannot measure the conflict rate from history |
| Bugs found on real machines | Supported: 59 test docstrings and 61 source comments describe a bug found live or on Windows; 23 Windows-only branches (`os.name == "nt"`, `win32`) in 10+ modules never run in CI |

## 1. Verdict per goal

Scale context first. Today's source code is already bigger than one context window: about
544k tokens of Python source, 359k of tests, 254k of frontend and 350k of Markdown (bytes/4).
At 1M lines (about 44 bytes per line here) the code alone is about **11M tokens**. If a
session spends about 150k tokens reading code for one change, it sees **about 1.5% of the
codebase**. Everything below is judged against that.

### 1.1 Complexity isolated by architecture: **partial (about 4/10)**

What holds:
- Package layering is real and enforced: `lint-imports` with 5 contracts, and the ignore list can
  only shrink (`unmatched_ignore_imports_alerting` defaults to error). Only 3 known upward
  imports.
- Package-level fan-out is moderate: `tools` depends on 3 packages, `runtime_lg` on 4.

What does not:
- **Packages have no public interface.** Of 205 cross-package imports, 165 go into a submodule
  rather than through the package (`tools` 60 deep vs 7 via package, `runtime` 50 vs 7,
  `workflows` 19 vs 0, `code_runtime` 11 vs 0). 14 imports reach a *private* name in another
  module (`web/app.py` imports `cli._dotenv_path`; `workflows/engine.py` imports
  `tools.scripts._run_python_script`; `spreadsheets.py` and `_chart_data.py` import
  `documents._split_table_row`). So a session cannot read "the interface"; it has to read the
  implementation.
- **Transitive closure is the whole program at the top.** `web.app` depends on 118 of 126
  modules, `web.routes.connectors` on 104, `conversation.session` on 96, `coordinator` on 54.
- **Composition happens in giant closures.** `build_presentation_tools` is 1,471 lines,
  `create_app_lg` 731 lines with branch complexity 106 (my AST count), the settings router 511
  (89), the connectors router 386 (105). A closure cannot be read, tested or owned in parts.
- **File sizes.** 7 own files over 1,000 lines. `tools/presentations.py` is 7,092 lines / 330 KB
  (about 85k tokens: one file costs about 8% of the window), `conversation/session.py` 3,755 lines
  with 92 methods on one class (`ChatSessionLG`), `tools/documents.py` 1,938. A presentation
  change today means reading `PPTX_DESIGN.md` (237 KB), `presentations.py` (330 KB) and
  `test_presentations_tool.py` (262 KB): **about 210k tokens before writing a line.**
- Functions: 1,591 in total, median 12 lines; 39 over 100 lines, 19 over 200; 33 with branch
  complexity over 20. `ruff --select C901` (default limit 10) reports 60.
- One import cycle inside `tools`: `documents` <-> `_chart_data`.
- The WebSocket protocol, the main frontend/backend contract, is untyped on the backend
  (`EventSink.send_json(data: Any)` in `conversation/events.py`) and hand-mirrored in
  `frontend/src/types/wire.ts` (38 event types). No test ties the two together.
- Frontend: flat `components/` (52 files), `App.tsx` 1,083 lines with 42 hook calls,
  `ConnectorsTab.tsx` 1,369, `ChatLog.tsx` 1,166; `types/settings.ts` is imported by 30 files.

Gap to 1M lines: component boundaries with enforced public interfaces, file and function
budgets, and splitting the 5–6 god files. Without these, the "read a slice" model fails
first on exactly the files that change most.

### 1.2 The floor held by tools: **good base, missing the ratchets (about 5/10)**

Held today: `tsc -b`, oxlint (2 rules configured), ruff (`E,F,I,UP,B`), mypy `strict` with
`warn_unused_ignores`, import-linter, the full pytest suite on every PR, a route-table
snapshot (`tests/web_routes.txt`), a frozen-archive hash and log-format test
(`tests/test_docs_layout.py`), prompt-cache identity tests (`tests/test_prompt_cache.py`).

Missing (verified absent): coverage measurement, mutation testing, size/complexity limits,
dead-code detection, dependency/licence/vulnerability scanning in CI, a snapshot of the
model-facing tool schemas (invariant 0001 is checked for *identity across conversations*, not
for *unintended change*), frontend unit tests, a Windows job, any doc–code consistency
check, a flaky-test policy.

Evidence that rules without tools rot:
- **Stale references**: 126 references to 6 files that no longer exist, in about 50 files.
  `web/session.py` (moved to `conversation/` on 2026-10-09) is still named 72 times in 35
  files, including `frontend/src/types/wire.ts`, the docstring at the top of
  `conversation/session.py`, and `config.py`. `office-agent/CLAUDE.md` still points readers to
  `test_web.py`, which was split into `tests/web/`.
- **The comment rule** ("WHY only, never history") is broken in 61 source comments that narrate
  "real bug, live-reported" history.
- Suppressions: 44 `type: ignore` and 143 `noqa` in `src` (no baseline, so growth is unseen).

Gap: the floor exists but nothing stops it from sinking a little in each PR. At 1M lines,
with many sessions, "a little per PR" is the main failure mode.

### 1.3 Communication cost cut by process: **written well, practised partly (about 4/10)**

Good: one start file (`AGENTS.md`, imported by `CLAUDE.md`), decision records 0001–0008 that are
short and specific, a one-file-per-change log (`docs/log/`), a short `plan.md`, area-prefixed
branches and PR titles, a written rule for red `main`, a 600-line PR guideline.

Practised partly:
- **Claiming via `task` issues has never been used: the repository has 0 issues.** The open-PR
  list is the only board, and it lost one piece of work (#64 duplicated #63).
- PR size: median 195 changed lines, but p90 1,892 and 17 of 66 PRs over 600 lines.
- Lead time is short (median 0.8 h from open to merge, p90 8.4 h). That is good for
  throughput, but it also means the maintainer merges quickly, so review is mostly CI.
- **Review results are not recorded.** See 1.2. Neither the maintainer nor a later session can
  tell whether an invariant-path change was reviewed or what was found.
- **The "not verified" debt is unmanaged.** 33 of 37 log entries list unverified items (46
  in total). Only a handful reach `docs/plan.md`; nothing tracks when one was verified.
- Codex sessions do not see `office-agent/CLAUDE.md` (the detailed rules): Codex reads
  `AGENTS.md` files from the root down, and `office-agent/` has no `AGENTS.md`. Only the root
  file tells them to go and read it.
- The long reference docs cannot be read whole: `runtime_lg/README.md` 3,658 lines,
  `PPTX_DESIGN.md` 3,544, `office-agent/README.md` 2,125.

Gap to many parallel sessions plus a second human: claiming, ownership, recorded review, a
ledger of what was not verified, and docs a session can load per component.

### 1.4 Refactoring made safe by tests: **good tests, unmeasured strength (about 5/10)**

Honest sample: I read 26 randomly chosen tests (seeds 7 and 31, script in the appendix):

| Kind | Count | Examples |
|---|---|---|
| Behaviour through a public entry point (tool by name, HTTP/WS API, store API); would catch a behaviour change and survive a refactor | 18 | `test_secret_store.py::test_a_session_environment_is_checked` (table of invalid inputs, state unchanged afterwards); `web/test_threads.py::test_deleting_a_conversation_forgets_who_may_message_it`; `web/test_chat.py::test_edit_file_batch_tool_works_end_to_end_through_the_agent_lg` |
| Behaviour, but via a private function (`_check_low_contrast`, `_clean_title`); catches regressions, breaks on rename/move | 2 | `test_presentations_tool.py::test_check_low_contrast_...`, `test_title_length.py::...` |
| Coupled to internals through a patched module path; a pure refactor breaks it | 2 | `web/test_connectors.py` patches `"coscribe.runtime_lg.mcp.connect_one_mcp_server_lg"`; `test_websearch_tool.py` patches `ddgs.ddgs.DDGS.__init__` |
| Interaction/protocol (asserts calls made), acceptable because the calls are the external protocol | 1 | `test_browser_panel.py::test_resize_skips_...` |
| Weak: no assertion (crash-only) or "file exists and size > 0" | 2 | `test_add_pptx_audio_two_calls_do_not_crash...`; `test_write_xlsx_generates_real_preview_via_libreoffice` |
| Restates configuration (metadata table) | 1 | `test_xlsx_gap_filling_tools_are_medium_risk_and_require_approval` (still useful: pins an approval rule) |

So about 20 of 26 would catch a behaviour change; only 1 merely restates the implementation.
Across the whole suite: 15 tests have no assertion at all, 42 `monkeypatch.setattr("coscribe.…")`
string targets into internals (11 into `runtime_lg.mcp`), 28 import lines in tests take private
names. Two tests wait on real 60-second timeouts
(`test_mcp_lg.py::test_mcp_server_connection_connect_times_out...` and
`::test_connect_one_mcp_server_lg_reports_a_clear_error_on_timeout`).

**Coverage, measured** (pytest-cov, branch mode, full suite; 2 tests deselected because my
coverage tooling on `PYTHONPATH` polluted the script-environment package list they check):
own code (vendored `_native_*` and `gemini_provider.py` excluded) has **91.3% line and 83.1%
branch coverage** over 17,445 statements. By package: `workflows` 94.9/89.3, `code_runtime`
95.0/85.6, `runtime` 94.1/87.1, `runtime_lg` 93.2/84.9, `conversation` 87.4/81.5, `web`
82.4/70.1, `tools` (with vendored) 79.8/64.1. Weakest own files: `web/browser_panel.py` 36%,
`cli.py` 75%, `web/app.py` 78%, `web/routes/scheduled.py` 80%, `tools/_xlsx_lookup_formulas.py`
81%. The vendored formula parser is at 23% (1,551 statements), so most of it is untested here.
High coverage, so the next question is whether the covered lines are actually *checked*.

**Mutation test, measured.** I ran mutmut 3.8.0 on `runtime/secret_store.py` (348 lines, part
of invariant 0003) against `test_secret_store.py`, `test_http_request.py` and
`test_connector_secrets.py`, in a scratch copy: 444 mutants in 2.5 minutes on 2 workers;
**299 killed, 142 survived, 3 not covered: a mutation score of 68%.** Of the 142 survivors, 78
only change an error message (noise; a real setup excludes message strings). The other 64 are
informative:
- `encoding="utf-8"` → `encoding=None` survives in every read and write of `secrets.json` and
  the session environment files. On Linux the default encoding is UTF-8, so no Linux test can
  see it; on a Chinese-locale Windows machine it is the GBK bug class this project has already
  hit. Mutation testing on Linux cannot close this; a lint rule can: ruff `PLW1514`
  (`unspecified-encoding`, preview) finds exactly 1 violation in the whole repository today
  (`tests/test_code_runtime.py:388`), so it can be turned on now at no cost.
- Boundaries are untested: `len(value) < MIN_VALUE` → `<=` survives, although 0003 states "a
  value is at least 8 characters"; the same for the host and variable limits.
- Redaction forms: dropping `safe=""` from the percent-encoded form, or changing the slice of
  the JSON-escaped form (`json.dumps(value)[1:-1]` → `[2:-1]`), survives. Those encodings are
  part of the promise in 0003 and no test pins them.
- `detach_everywhere`: `continue` → `break` and `and` → `or` survive.

This is one module; I would expect similar numbers elsewhere (guess). The point is not that
the tests are bad (the sample above says they are mostly good), but that "about 1,900 tests,
green" does not tell a refactoring session which behaviours are actually pinned. Note also that
mutmut's trampolines broke `tests/test_tool_deferral.py` in a first attempt, because tool
schemas are built by introspecting functions; tool-defining modules need cosmic-ray or an
exclusion.

Missing for refactors specifically: golden-file (characterization) tests of the generated
`.pptx/.docx/.xlsx` XML (tests read files back through python-pptx/openpyxl, which is good for
behaviour but blind to XML that the library ignores and PowerPoint does not), a snapshot of
the tool schemas, a typed WebSocket contract, frontend unit tests for the pure logic
(`state/reducer.ts` 733 lines, `lib/transcriptGrouping.ts` 718 lines), and property tests for
the formula code (`_xlsx_lookup_formulas.py`, `_native_formula/`).

---

## 2. Bounded-context design

### 2.1 Target

A typical change or review should need **at most about 150k tokens of reading, from at most
about 15 files, found without searching blind**:

| Slice part | Budget |
|---|---|
| Root `AGENTS.md` + detailed rules + `plan.md` | ≤ 10k tokens (today about 8k, fine) |
| Module card(s) of the touched component(s) | ≤ 2k each, at most 3 |
| Public interface files of the components it calls | ≤ 15k total |
| Files changed | ≤ 8 files, each ≤ 800 lines (about 10k tokens) |
| Their tests | ≤ 40k |
| Review only: diff + the above, without the dependency interfaces | ≤ 100k |

Corollary: a **component** (the unit a session owns for one change) is about 5–20k lines,
small enough that its card plus interface stays near 15k tokens. At 1M lines that is 50–150
components, so components need a second level: **area** (today's packages: `tools`, `web`,
`conversation`, …) contains components (`tools.office.pptx`, `tools.exec.scripts`, …).

### 2.2 Package and module boundaries

Rules (all checkable, see §3):
1. A component is a Python package with an `__init__.py` that defines `__all__`. That file **is**
   the public interface. Other components import only from it (`from coscribe.tools.office.pptx
   import build_presentation_tools`), never from a submodule or a `_private` name.
2. Files: soft limit 800 lines, hard limit 1,500 (ratcheted, existing offenders listed and only
   allowed to shrink). Functions: 80 lines / branch complexity 15.
3. A component's tests live next to its name: `tests/<area>/<component>/`, so "which tests
   protect this" is a path lookup, not a search.
4. Closures that build tool lists stay, because the tool docstrings are the model-facing
   schema (0001), but each closure becomes a thin adapter of at most a few hundred lines over
   a toolkit class split by concern.

Concrete splits of the largest files:

| File (lines) | Split into | Boundary |
|---|---|---|
| `tools/presentations.py` (7,092) | package `tools/office/pptx/`: `animation.py` (presets, timing tree, audio: today about lines 654–1,296), `qa.py` (render to PDF, overflow, overlap, contrast, missing visuals: 1,297–1,383 and 2,386–2,722), `theme.py` (theme tokens, scheme colours, CJK fix, transitions: 1,460–1,786), `layouts.py` (bullet/table/icon/stat/two-column slide builders: 1,786–2,386), `inspect.py` (describe shapes, SmartArt: 2,722–3,080), `templates.py` (slide duplication, template adjust: 3,137–3,300), `effects.py`, `toolkit.py` (`PresentationToolkit`, itself split per tool group), `schema.py` (`build_presentation_tools`, the tool docstrings) | `__init__` exports `build_presentation_tools` and nothing else; `protected` contract on the submodules |
| shared Markdown parsing used by pptx, xlsx, charts (`documents.parse_blocks`, `_split_table_row`) | `tools/office/markdown_blocks.py` | removes `presentations -> documents` and `spreadsheets -> documents._private`, and the `documents <-> _chart_data` cycle; pptx, docx, xlsx become independent siblings |
| `tools/documents.py` (1,938) | `tools/office/docx/` and `tools/office/pdf/` | as above |
| `conversation/session.py` (3,755; `ChatSessionLG` with 92 methods) | `session.py` (facade, public methods used by `web` and `cli`), `approvals.py` (`_decide_*`, `_auto_review*`, `_effective_run_approval_mode`: about 600 lines, the security-relevant part, gets its own card and owner), `turn.py` (`_stream_turn`, hooks), `history.py` (edit, rewind, compact, clear), `inbox.py` (sub-agent reports, conversation messages), `workflow_drafting.py`, `skill_save.py` | collaborators get a narrow `Protocol` of what they need from the session instead of `self` |
| `web/app.py` `create_app_lg` (731-line closure) | `web/app.py` stays the composition root (about 150 lines). Thread sidecars become `conversation/thread_store.py`, connector connect/reconnect `runtime_lg/connector_manager.py`, the wake and scheduled poll loops `workflows/scheduler_loop.py` | services are classes with constructors, testable without FastAPI; routes receive them through `web/state.py` |
| `web/routes/settings.py` (685; one 511-line `router()`), `connectors.py` (386-line router) | one module per resource (`providers.py`, `secrets.py`, `environments.py`, `oauth_apps.py`) | route snapshot already guards the split |
| `coordinator.py` (975) | `coordinator/prompt.py` (instructions, frozen), `coordinator/tools.py` (fixed tool list, `CORE_TOOL_NAMES`), `coordinator/__init__.py` | the two halves of invariant 0001 become two small files a reviewer can read whole |
| frontend `App.tsx` (1,083), `ConnectorsTab.tsx` (1,369), `ChatLog.tsx` (1,166), `SkillsTab.tsx` (1,120) | `src/features/<feature>/` (chat, threads, settings/connectors, settings/skills, workflow, browser, tasks) each with an `index.ts`; `App.tsx` becomes layout plus routing; per-feature state slices out of `state/reducer.ts` | a dependency rule: features import each other only via `index.ts`; `lib/` and `types/` cannot import features |

Do these splits **after** the characterization tests of §4 exist, as pure-move PRs (see §6).

### 2.3 Module cards

One `AGENTS.md` per component, at most 60 lines, with fixed headings:

```
# <component>: <one line>
## Purpose            (what it owns; what it explicitly does not)
## Public interface   (names, identical to __all__)
## Depends on         (components; must match the import contracts)
## Invariants         (links to decisions/000N; what a change here must not break)
## Tests              (paths; which ones are characterization/golden)
## Verify by hand     (what CI cannot check: real Windows, a vendor sign-in)
## Reviewed           (commit sha when the card was last checked against the code)
```

Loading, verified against the Claude Code docs (code.claude.com/docs/en/memory, fetched today):
Claude Code loads a subdirectory's `CLAUDE.md` on demand when it reads a file there, but reads
a nested `AGENTS.md` **only if no `CLAUDE.md` exists at or above the working directory**, and
this repo has a root `CLAUDE.md`. Codex applies the nearest `AGENTS.md` to each changed file
(developers.openai.com/codex/integrations/github). So each component gets `AGENTS.md` (the
card) plus a one-line `CLAUDE.md` containing `@AGENTS.md`, the same pattern as the root. Also
add `office-agent/AGENTS.md` (the detailed rules) so Codex sees them.

Keeping cards from rotting, enforced by a test (`tests/test_module_cards.py`):
- every component package has a card with exactly these headings, at most 60 lines;
- the "Public interface" list equals `__all__` of the package;
- "Depends on" equals the component's actual imported components (from grimp);
- every path a card mentions exists (the same checker as for stale references, §3);
- staleness warning, not failure: if more than about 300 lines of the component changed since
  the `Reviewed` sha, CI prints a notice and the PR template asks the author to re-check it.

The long histories (`runtime_lg/README.md`, `PPTX_DESIGN.md`, `office-agent/README.md`) are
frozen like `docs/history/roadmap-through-2026-10-08.md`: still searchable, never required
reading. Whatever in them is still a live rule moves into a card or a decision record.

### 2.4 Contracts at boundaries

- **Model-facing tool schemas** (the cached prefix, 0001): a checked-in snapshot
  `tests/tool_schemas.txt` with every tool's name, risk tier, deferred/core, parameter
  names and types, the sha256 of its description, and the total token estimate. Any change
  shows up as a diff a reviewer can read in a minute; `UPDATE_SNAPSHOTS=1` rewrites it, the
  same pattern as `tests/web_routes.txt`.
- **WebSocket events**: `TypedDict` (or pydantic) models for the 38 events in
  `conversation/events.py`; export JSON Schema; generate `frontend/src/types/wire.gen.ts`; CI
  fails if the generated file differs from the committed one.
- **HTTP API**: FastAPI already produces OpenAPI; snapshot it (`tests/openapi.json`) and
  generate the REST types for `lib/rest.ts` the same way.
- **Office file output**: golden XML snapshots (§4).
- **Component interfaces**: a contract test file per public interface
  (`tests/<area>/<component>/test_interface.py`) that only uses names from `__all__`.

### 2.5 Dependency rules that scale

Five contracts do not scale to 100 components. Use what import-linter 2.15 (installed here,
released 2026-09-04) already offers, checked in the installed source:
- `layers` with `containers`: the same layer rule inside every area (e.g. in `tools.office`:
  `pptx | docx | xlsx | pdf` above `markdown_blocks | ooxml` above `common`), and
  `exhaustive = true` so a new component must be placed in a layer.
- `protected`: a component's submodules may be imported only by the component itself. This is
  the rule that turns `__init__.py` into the real interface. Start with the 165 current deep
  imports in `ignore_imports`; the list can only shrink.
- `independence` for siblings that must not know each other (pptx/docx/xlsx; the connectors).
- `acyclic_siblings` against cycles like `documents <-> _chart_data`.
- `broken_contract_guidance` on every contract: the text an AI session sees when it breaks
  the rule ("import from `coscribe.tools.office.pptx`, not a submodule; see the card").

Plus one small custom check (grimp, about 50 lines): **direct fan-out per module ≤ 25**
(baseline: `conversation.session` 43, `web.app` 34, `tools/__init__` 21, `web.routes.settings`
20), ratcheted. Generate the contracts for components from a single
`components.toml` (name, layer, owner, card path) so adding a component is one entry, and
`CODEOWNERS` is generated from the same file.

Frontend: `dependency-cruiser` (18.5.0) for the feature rule, or oxlint's
`no-restricted-imports` if it is enough; `knip` for unused exports.

### 2.6 Keeping large and generated data out of context

Tracked data that a session should never read whole: `tools/_native_animation_presets/animation_presets.json`
(559 KB), `skill_catalog.json` (173 KB), 27 OOXML `.xsd` files (up to 241 KB), the two
`package-lock.json`, `site/index.html` (283 KB), the frozen roadmap (613 KB).
- `.gitattributes` with `linguist-generated=true` for them (collapses them in GitHub diffs, so
  reviewers and review bots skip them).
- `.claude/settings.json` `permissions.deny` for `Read(...)` on these paths, so a session asks
  before loading one (Claude Code feature; I did not test it on this repo).
- A root `.ignore` file (ripgrep honours it; verify before relying on it) so `Grep` does not
  return hits from minified or data files.
- A size check: a tracked text file over 200 KB outside an allow-list fails CI.

---

## 3. Guardrail tooling, in priority order

The common mechanism for all of them is a **ratchet**: `quality/baseline.json` holds today's
numbers per file or package; CI fails if any number gets worse and prints the new, better
number when one improves, so the author lowers the baseline in the same PR. The baseline file
is in `CODEOWNERS`, and loosening it needs a human approval. This is what makes adoption
possible without a big-bang: nothing existing has to be fixed first.

The general way an AI session games a check is to **move the number, not the property**: an
`ignore` entry, a raised baseline, an assertion deleted, a test that executes code without
checking it, a file split arbitrarily at line 1,499. Each item below names its specific
gaming and the counter.

| # | Check | Catches | Adopt by | CI cost | Gaming, and the counter |
|---|---|---|---|---|---|
| 1 | **Ratchet runner** (`scripts/ratchet.py`, one JSON baseline) | the slow sinking of every number below | start with report-only for a week, then enforce | < 30 s | raising the baseline: baseline in CODEOWNERS; the PR template asks for the reason |
| 2 | **Coverage** (pytest-cov, branch) with a total floor ratchet and **diff coverage** ≥ 80% on changed lines (`diff-cover` 10.6.0) | new code without tests | floor = today's number rounded down (91% line / 83% branch on own code) | guess: +20–40% on a serial run; small once tests run under xdist | tests that run code without asserting: answered by #8 (mutation) and the assertion-less test check; `# pragma: no cover` counted as a suppression in the ratchet |
| 3 | **Size and complexity budgets**: ruff `C901` (max 15), `PLR0912`, `PLR0915`; file length script | god files and functions | per-file baseline of current offenders (ruff `per-file-ignores` generated, or the ratchet script) | seconds | splitting at the limit without meaning: the card and `protected` contract make arbitrary splits visible; review checklist item "does the split follow a concern" |
| 4 | **Architecture fitness**: the import-linter contracts of §2.5 plus fan-out ≤ 25 | erosion of boundaries | `ignore_imports` of today's violations; import-linter already fails on an unmatched ignore, so the lists only shrink | seconds (grimp is fast) | adding an ignore line: the file is in CODEOWNERS; the AGENTS.md rule "never add one without a decision record" already exists |
| 5 | **Doc–code consistency**: every file path in Markdown, docstrings and comments must exist; card interface = `__all__`; card deps = imports | the 126 stale references; rotting cards | fix the 126 in one docs PR, then enforce | seconds | deleting the reference instead of fixing it: acceptable, it is the right fix most of the time |
| 6 | **Public API snapshots**: tool schemas (§2.4), WS schema, OpenAPI, routes (exists), settings/env vars | silent changes to the provider-cached prefix (0001), to the frontend contract | generate today's snapshot | seconds | regenerating the snapshot without reading it: the snapshot diff is shown in the PR body by a CI step, and a change to `tool_schemas.txt` is a CODEOWNERS path |
| 7 | **Assertion-less and patch-target lint**: a test must contain an assert/raises; `monkeypatch.setattr("coscribe.…")` string targets are counted | crash-only tests, refactor-fragile tests | baseline 15 and 42 | seconds | `assert True`: count trivially-true asserts as well |
| 8 | **Mutation testing** with mutmut 3.8.0 (2026-09-12; POSIX-only, needs `fork`, fine on Linux CI) | tests that cover but do not check | nightly on the invariant modules: `runtime/secret_store.py`, `runtime/secrets.py`, `runtime_lg/exec_policy.py`, `code_runtime/permissions.py`, `tools/script_guard.py`, `workflows/spec.py`, `_xlsx_lookup_formulas.py`; then on PRs for changed invariant files only | measured: `secret_store.py` 444 mutants in 2.5 min on 2 workers; the 9 invariant modules (2,835 lines) extrapolate to about 15–25 min on 4 workers (guess); budget 30 min nightly | killing mutants with tests that restate the code (asserting exact internal strings): review the killing test; prefer survivors to be killed by public-interface tests. Note: mutmut's trampolines broke `tests/test_tool_deferral.py` in my run, because tool schemas come from function introspection; exclude introspected tool functions or use cosmic-ray (8.7.0) for those |
| 9 | **Dependency, licence and secret scanning**: Dependabot, `pip-audit` (2.10.1), `npm audit`, CodeQL and secret-scanning push protection (free for public repositories), a licence allow-list check | vulnerable or incompatibly licensed packages; leaked keys | settings plus one weekly workflow; findings become issues, not PR failures, at first | 2–5 min, weekly and on lockfile changes | dismissing alerts: dismissals need a comment; reviewed monthly by the human |
| 10 | **Dead code**: `vulture` (2.16) with a whitelist baseline; `knip` for the frontend | leftovers after refactors | whitelist of today's findings | < 1 min | adding to the whitelist: ratcheted count |
| 11 | **Flaky-test policy**: a test that fails then passes on rerun is reported (rerun once in CI, record it), quarantined with `@pytest.mark.quarantine(issue=N, until=date)`, and fixed within a week; ban wall-clock assertions (`elapsed <`) | the PR #5 class of failure (a 1.0 s timing assert on slow runners) | start with the rerun report | small | quarantining forever: the marker requires an expiry date, an expired quarantine fails |
| 12 | **CI speed** (below) | 12 min today, an hour at 1M lines | | | skipping tests by selection: full suite always on `main` and nightly |
| 12b | **Platform lints** that run on Linux but catch Windows bugs: ruff `PLW1514` (unspecified encoding; preview rule, enable with `lint.preview = true` and `explicit-preview-rules = true`), and a ban on `shell=True` and bare `"python"` / `"node"` executable names outside the `_office_bins`/`script_env` helpers | the GBK/UTF-8 and PATH bug classes seen live | 1 violation today for `PLW1514` | seconds | `# noqa`: counted by the ratchet |
| 13 | **Windows job** (`windows-latest`, free for public repos, 4 CPU/16 GB, verified) running the platform-sensitive tests on PRs that touch those modules and the full suite nightly | the PATH, encoding, `cmd`/`taskkill`, Credential Manager class of bug | nightly first, required later | about 15–25 min (guess) | none specific; keep it required once green for two weeks |

**CI speed.** Today pytest runs on one core of a 4-core runner (public repositories get 4
CPUs and 16 GB, verified on docs.github.com). In order:
1. Fix the two 60-second real timeouts in `test_mcp_lg.py` (inject the timeout): saves 2 min.
2. `pytest-xdist -n 4`. **Measured here** (a 4-CPU VM, same as a public-repo runner): the full
   suite passed under `-n 4` on the first try, **1,856 passed in 3 min 50 s**, against 14 min 49 s
   serial with coverage and about 8–9 min serial in CI. One clean run does not prove there is
   no shared state; run it 5 times before making it the default.
3. Split `check.sh` into parallel jobs (frontend build + oxlint, Python lint/mypy/import
   contracts, pytest shards with `pytest-split` 0.11.0 using stored durations) and keep one
   aggregate job named `test`, which is the required check in the ruleset.
4. Test selection by changed component on PRs: map changed files to components, take the
   components that depend on them (grimp `find_upstream_modules` inverted), run their tests;
   `pytest-testmon` (2.2.0) is the finer-grained alternative. Always run the full suite on
   `main` and nightly; a selected-only PR that breaks `main` is reverted by the existing rule.
5. Reduce import time (65 s to collect 1,858 tests locally) by making heavy imports lazy in
   test modules.

Merge queue would make "selected tests on PRs, full suite before merge" safe, but GitHub's
merge queue is available only for public repositories owned by **organizations** (and
Enterprise Cloud); this repository is owned by a user account (verified via the API and the
GitHub changelog of 2023-07-12; I found no newer statement either way). See §9.

---

## 4. Refactor-safe testing strategy

What protects a refactor in this codebase, in order of value per effort:

1. **Characterization (golden) tests before every split.** Before splitting
   `presentations.py`, generate about 20 representative decks through the public tools
   (every layout directive, a template, animation, transition, audio, SmartArt edit, theme),
   unzip, canonicalise the XML (sorted attributes, stable relationship ids, no timestamps),
   and commit it under `tests/golden/pptx/`. The same for docx (tracked changes, formulas,
   charts, CJK) and xlsx (formulas, merges, validation, conditional formats). A pure move must
   leave every golden byte-identical. This also catches XML that python-pptx or openpyxl
   ignore on read-back but PowerPoint or Excel reject, a class of bug the read-back tests
   cannot see.
2. **Decision tables for the approval logic.** `ChatSessionLG._decide_action_request` (290 lines,
   complexity 35) decides what runs without asking. Before moving it, write a parametrised
   test over (permission mode × risk tier × folder guard × connector policy × auto-review ×
   sub-agent) → decision, run through the public session API with a fake model. That table is
   both the safety net and the spec a reviewer checks.
3. **Contract tests at component interfaces** (§2.4), using only `__all__` names. These
   survive internal refactors by construction.
4. **Snapshots of the model-facing surface**: tool schemas, system prompt, routes, OpenAPI,
   WebSocket schema.
5. **Property tests** (Hypothesis 6.168.5) where the input space is large and a reference
   exists: the formula parser and evaluator (`_native_formula/`, `_xlsx_lookup_formulas.py`:
   parse/print round trip; evaluation against LibreOffice's recalculation on generated
   formulas), the Markdown-to-blocks parser (round trip), redaction of secrets in tool output
   (any encoding of a stored value in any position is blanked: an invariant of 0003, ideal
   for property testing), path guards (no generated path escapes the workspace).
6. **Frontend unit tests** (vitest 5.0.3) for the pure logic: `state/reducer.ts`,
   `lib/transcriptGrouping.ts`, `lib/rest.ts`. The 17 Playwright specs should run in CI against
   `scripts/stub_llm.py` (nightly at first).

Telling good AI-written tests from bad, automatically:
- **Mutation score of the changed lines**: a test that does not kill any new mutant adds
  nothing. This is the only signal that cannot be satisfied by restating the code without
  checking it.
- **Fails-before check**: CI runs the PR's new tests against the base commit's source; a
  bug-fix PR whose new test passes on the base has not reproduced the bug. (Cheap: check out
  `src/` from the base, run only the new test ids.)
- **Coupling lint**: new private-name imports and `monkeypatch.setattr("coscribe.…")` string
  targets count against the ratchet.
- **Assertion density**: no assertion, or only `is not None` / `len(x) > 0`, is flagged.

PR policy (put into the PR template and `office-agent/CLAUDE.md`):
- A bug fix includes a test that fails on the base commit (checked by CI, not by trust).
- A behaviour change includes or updates a public-interface or golden test.
- A refactor PR changes **no test files** except mechanical import-path updates, and every
  golden stays identical. Test changes in a refactor PR go in a separate PR first.
- Changed lines reach 80% branch coverage (diff-cover), or the PR says why not.
- Invariant paths: mutation run on the changed file, survivors listed in the PR.

---

## 5. AI review design

Today's independent review is the same model family, prompted by the maintainer, results
not recorded. Correlated blind spots are the core problem: a reviewer from the same family
tends to accept the same wrong assumption the author made. Design:

**Input package** (`scripts/review_pack.py <PR>`, about 100k tokens at most): the diff; the
cards of the touched components; their `__init__.py` interfaces; the decision records linked
from those cards; the snapshot diffs (tool schemas, routes, OpenAPI, WS); the ratchet report;
the list of new tests and whether each fails on the base; the PR's "Not verified" section.
The reviewer reads that, not the repository.

**Roles**, each a separate run with its own prompt:
1. *Spec reviewer*: does the change do what the linked issue's "Done when" says, and nothing
   else? (Catches scope creep and misunderstanding of intent; needs a real issue, which today
   does not exist.)
2. *Invariant reviewer* with a per-area checklist kept in the card ("Invariants" section):
   e.g. for `runtime_lg/tool_deferral.py`, "no per-conversation data in schemas or prompt",
   for secrets "no value leaves through a result, an env var, a log", for routes "no listener
   on a non-loopback address".
3. *Adversarial reviewer*: told to break the change and to **prove each finding with a failing
   test**. A finding counts only if its test fails on the PR head. This turns opinions into
   evidence and removes most false positives.
4. *Mutation-guided*: survivors on the changed lines are given to the author to kill or to
   explain.

**Model diversity.** For invariant paths, run one reviewer from a different model family.
Verified option: Codex code review in GitHub (`@codex review`, or automatic reviews; it reads
review guidelines from `AGENTS.md`, nearest file per changed file; flags P0/P1 only;
developers.openai.com/codex/integrations/github). The repository already depends on Codex as a
runtime (0005), so the account exists. Diversity does not remove shared blind spots; it
reduces them.

**Recording.** Every review is posted as a GitHub PR review (inline comments with a severity).
Turn on `required_review_thread_resolution` in the ruleset so a finding cannot be silently
ignored; the author resolves with a fix or a reason. A weekly script collects findings,
outcomes and escaped defects into `docs/metrics/`.

**What AI review cannot be trusted to catch**: whether the feature is what the user wanted;
real-machine behaviour (Windows PATH, GBK/UTF-8, keychain, Electron window state, LibreOffice
versions); vendor behaviour (OAuth quirks, model API changes); security of the no-sandbox
design under prompt injection through documents, web pages and connector results (an
approved script can do anything the user can, 0002); interactions between two PRs that are
each correct; cost regressions in live model use; UI look and feel.

**Is review working? Metrics**:
- escaped defects: bugs fixed later whose cause is traced to a reviewed PR (label `escaped`
  on the fix PR, linking the origin);
- finding precision: accepted findings / all findings (below about 30% means noise and authors
  learn to ignore it; near 100% with few findings means it is too timid);
- adversarial yield: proven (failing-test) findings per 1,000 changed lines;
- seeded-bug recall: once a month, plant 3 known bugs (as in the OCR evaluation in
  `office-agent/CLAUDE.md`) in a scratch PR and measure how many each reviewer finds;
- review cost per PR (tokens/money) and added lead time.

Cost: guess, not measured. About 100k input tokens per role; three roles on invariant PRs
(about 1 in 8 PRs today) and one role (adversarial) on the rest. At today's 10–40 PRs a day
that is affordable; it is the first thing to cut by selecting roles by path.

---

## 6. Process for many parallel sessions and a second human

Changes to make (all small, mostly in `AGENTS.md`, `CONTRIBUTING.md`, `office-agent/CLAUDE.md`):

1. **Claiming that is used.** Every PR body has `Closes #N` or `Part of #N`, and a CI step warns
   if not. A session that starts work without an issue opens one (title, area, hot files) before
   its first commit. Rationale: 0 issues so far, one duplicated PR.
2. **Ownership map**: `components.toml` → generated `CODEOWNERS` (one line per component, owner
   = a human) and generated `docs/components.md` (component, card, owner, layer). Sessions
   find their slice from it.
3. **Discovery protocol in `AGENTS.md`** (replace "read this first, about 15 minutes"):
   1. read root `AGENTS.md`; 2. find the component in `docs/components.md`; 3. read its card;
   4. read the interfaces it lists; 5. open implementation files only for the component you
   change; never read a file over 1,500 lines whole, and never read `docs/history/` or the
   frozen READMEs except by `grep`. Provide `scripts/slice.py <path>` that prints the card,
   interface, tests and dependents of a file.
4. **Hot files go away by design**, not by etiquette: after the splits, `web/app.py`,
   `conversation/session.py` and `coordinator.py` become small composition files. Until then
   keep the "Touches:" line and add a `freeze` label: an issue labelled `freeze` lists paths;
   a CI step warns when a PR touches a frozen path (about 30 lines with `gh api`).
5. **Large refactors**: an announcement issue (template `refactor`): paths frozen, expected
   duration, the characterization tests that will guard it, the sequence of pure-move PRs. A
   pure-move PR may exceed 600 lines if a script (`git diff --color-moved` / a move detector)
   shows that at least 95% of it is moved text.
6. **Not-verified ledger**: each "Not verified" bullet in a log entry becomes an issue with
   label `needs-real-machine` (or `needs-account`) and the platform. The human closes them
   when checked. The plan lists only the count and the oldest.
7. **Recorded review**: the independent review is a GitHub review (§5); "needs an independent
   review" in a PR body is replaced by a required label `review:independent-done`.
8. **Second human (0007)**: accept it; add them to `components.toml` as owners of some
   components; turn on `require_code_owner_review` for invariant paths and for
   `quality/baseline.json`, `tests/tool_schemas.txt`, `pyproject.toml [tool.importlinter]`,
   `.github/`.
9. **Metrics, weekly, by a scheduled session** into `docs/metrics/<week>.md`: PR lead time
   (median/p90), PR size, duplicate/closed PRs, reverts, time `main` was red, CI p90 duration,
   flaky reruns, ratchet trend, escaped defects, not-verified ledger size and age, review
   precision. Conflict rate: count PRs whose branch contains a merge commit from `main` that
   touched files also changed on the branch (visible in the PR's commit list before squash).

---

## 7. What AI alone cannot solve

Blunt list of risks that remain at 1M lines with a maintainer who only merges:

1. **Intent and spec errors.** AI sessions build what the issue says; a wrong issue becomes
   correct-looking wrong code with passing tests and a green review. No tool catches it.
2. **Security of the no-sandbox design (0002).** The model writes scripts that run as the user,
   and reads untrusted documents, web pages and connector results. Prompt injection that leads
   to an approved harmful action is a design-level risk; reviewers check code, not the
   threat model. Secrets promise only that the model cannot *see* a value (0003). This needs a
   human-owned threat model and a periodic human (or external) review.
3. **Real-machine behaviour.** 23 Windows branches never run in CI; many past bugs were
   found only on Windows or in live use. A Windows CI job helps with PATH and encoding, not
   with a user's Credential Manager, antivirus, corporate proxy, Office versions or display
   scaling.
4. **Vendor drift.** 32 catalog connectors (13 + 19 per `plan.md`), whose sign-in is mostly
   unverified, plus several model APIs that change names, limits and caching behaviour.
   Tests use fakes; fakes do not drift. Needs scheduled live probes with real accounts, owned
   by a human.
5. **Correlated blind spots.** Author and reviewer from the same family share assumptions;
   adding a second family reduces, not removes, this.
6. **Cost.** CI minutes are free for this public repository (verified), but review and live
   tests cost tokens and money, and at many sessions a day the review bill can exceed the
   authoring bill.
7. **Architecture drift by local optimisation.** Each session optimises its slice. Without a
   human who reviews the component map once a month, boundaries are moved one reasonable PR
   at a time.

**Minimum human involvement I would insist on**:
- About 2 hours a week on a real Windows machine: install the latest build, run a fixed smoke
  checklist (sign in to two connectors, run a script, write and open a pptx/docx/xlsx in
  Office, secrets page), and close or re-file `needs-real-machine` issues.
- Approve every decision record, every loosening of a baseline, and every change to tool
  schemas, the system prompt, secrets, approvals, or network listeners (from the review
  summary, not by reading all the code).
- Write or approve the "Done when" of task issues for anything user-visible.
- Once a month, 1 hour: read the metrics page and the component map.
- Once a quarter: a security review of the no-sandbox, secrets and OAuth paths.

**Signals that the approach is failing**: escaped defects rising for three weeks; reverts
above about 5% of merges; ratchet loosening requests becoming routine; mutation score
falling on invariant modules; the not-verified ledger growing faster than it is closed;
duplicate or closed-unmerged PRs above about 5%; review precision very low (noise) or very
few findings over many weeks (rubber stamp); CI p90 above 20 minutes; cards failing their
consistency check repeatedly; sessions reporting that they had to read files over 1,500 lines.

---

## 8. Ordered roadmap

Each step is one reviewable PR or less; steps 1–5 can start now and have no dependencies on
each other except where noted. HOT = touches a hot file; INV = touches an invariant path or a
CODEOWNERS path.

| # | Step | Files | Verify | Risk | Depends |
|---|---|---|---|---|---|
| 1 | **Measure and ratchet (report-only)**: `scripts/ratchet.py` computing file sizes, function length/complexity (ruff C901 JSON), fan-out, deep cross-package imports, private imports, suppressions (`type: ignore`, `noqa`, `pragma: no cover`), assertion-less tests, `monkeypatch` string targets, stale path references; `quality/baseline.json`; one line in `check.sh` that prints but does not fail. Also turn on ruff `PLW1514` (1 fix needed) | `scripts/ratchet.py`, `quality/baseline.json`, `scripts/check.sh`, `pyproject.toml` (ruff), `tests/test_code_runtime.py`, `.github/CODEOWNERS` | numbers match this report; CI time +< 30 s | low | none. INV (CODEOWNERS) |
| 2 | **Coverage in CI**: pytest-cov branch coverage, total floor = measured, diff-cover on PRs (report first, enforce after a week); fix the two 60 s timeouts in `tests/test_mcp_lg.py` in the same PR to pay for the overhead | `pyproject.toml` (dev deps), `scripts/check.sh`, `.github/workflows/office-agent-ci.yml`, `tests/test_mcp_lg.py` | CI shows the coverage number; wall time not above today's | low | none. INV (workflow) |
| 3 | **Fix the 126 stale references and enforce the checker** (docs and comments only; also removes history narration from the docstring of `conversation/session.py`) | about 50 files, comments/docs only; `tests/test_doc_references.py` | checker passes; no code change (`git diff` shows comments and Markdown only) | low; HOT by line count but comment-only | 1 (uses the checker) |
| 4 | **Tool-schema and system-prompt snapshot** (`tests/tool_schemas.txt`, plus a token estimate), and a line in decision 0001's Consequences | `tests/test_tool_schema_snapshot.py`, snapshot file, `docs/decisions/0001-…` | changing any tool docstring makes the test fail with a readable diff | low | none. INV-adjacent (0001) |
| 5 | **Make review and "not verified" traceable**: PR template gets "Issue: #", "Independent review: link" and "Not verified → issues"; `office-agent/CLAUDE.md` says the independent review is posted as a GitHub review; label set (`task`, `needs-real-machine`, `escaped`, `freeze`, `review:independent-done`); one issue per open not-verified item from `plan.md`; ruleset `required_review_thread_resolution: true` (admin setting) | `.github/PULL_REQUEST_TEMPLATE.md`, `office-agent/CLAUDE.md`, `CONTRIBUTING.md`, `AGENTS.md` | the next invariant-path PR has a recorded review | low | none. INV (rules text) |
| 6 | **CI speed**: xdist `-n 4` (after fixing tests that are not parallel-safe), parallel jobs with one aggregate `test` job; nightly full run | workflow, `check.sh`, `pyproject.toml`, a few tests | CI p90 under 7 min; `test` still the required context; 5 consecutive green `-n 4` runs | low to medium (passed once here under `-n 4`; hidden shared state may still show up) | 2 |
| 7 | **Component map and first module cards**: `components.toml`, generated `docs/components.md` and `CODEOWNERS`; cards (+ `CLAUDE.md` with `@AGENTS.md`) for `runtime`, `runtime_lg`, `conversation`, `web`, `tools`, `workflows`, `code_runtime`; `office-agent/AGENTS.md`; card checker test; new discovery protocol in root `AGENTS.md` | new Markdown files, `tests/test_module_cards.py`, `AGENTS.md`, `.github/CODEOWNERS` | checker passes; a fresh session asked to make a small change reports which files it read (target ≤ 15) | low | 3. INV (CODEOWNERS) |
| 8 | **Import contracts that scale**: `protected` contracts per package with today's deep imports as shrinking ignore lists, `acyclic_siblings`, `broken_contract_guidance`; fan-out ≤ 25 in the ratchet; break the `documents <-> _chart_data` cycle by moving the table-row helpers to `tools/_markdown_tables.py` | `pyproject.toml`, `tools/documents.py`, `tools/_chart_data.py`, `tools/spreadsheets.py` | `lint-imports` passes; ignore lists only shrink | low | 1. INV (import rules) |
| 9 | **Golden-file tests for pptx/docx/xlsx** (about 20 decks, 10 docs, 10 workbooks; canonical XML) | `tests/golden/`, `tests/test_office_golden.py`, a canonicaliser | goldens stable across two CI runs and on a second machine | medium (non-determinism in generated XML) | none |
| 10 | **Approval decision table** for `_decide_action_request` through the public session API | `tests/conversation/test_approval_table.py` | each row fails when its branch is mutated (mutmut on `session.py` approvals, run by hand) | low | none |
| 11 | **Split `presentations.py`** into `tools/office/pptx/` as 4–6 pure-move PRs (QA checks, animation, theme/transitions, layouts, inspect/templates/effects, then the toolkit), announced with a `freeze` issue | `tools/presentations.py` → new package; `tools/__init__.py`; import paths in tests | goldens byte-identical; tool-schema snapshot identical; route snapshot identical | medium | 4, 9. HOT (`tools/__init__.py`), INV-adjacent (tool docstrings must not change) |
| 12 | **Split `ChatSessionLG`**: approvals first (`conversation/approvals.py` behind a `Protocol`), then history, inbox, workflow drafting | `conversation/session.py` + new modules | decision table and all `tests/web/` pass unchanged | high (the core loop) | 10. HOT, INV (approvals) |
| 13 | **Thin `create_app_lg`**: services (`thread_store`, `connector_manager`, `scheduler_loop`) out of the closure; split the settings and connectors routers per resource | `web/app.py`, `web/routes/*`, new service modules | route snapshot identical; `tests/web/` unchanged | medium | 8. HOT, INV (network listener code nearby) |
| 14 | **Typed WebSocket contract**: event `TypedDict`s in `conversation/events.py`, JSON Schema export, generated `wire.gen.ts`, CI diff check; vitest for `reducer.ts` and `transcriptGrouping.ts` | `conversation/events.py`, emitters, `frontend/src/types/`, `frontend/package.json` | changing an event field fails `tsc -b`; vitest runs in `check.sh` | medium | 6 |
| 15 | **Nightly guardrails**: mutation testing on the invariant modules (survivors to an issue), Windows pytest job, Playwright e2e against `stub_llm.py`, `pip-audit`/`npm audit`, Dependabot, CodeQL, secret scanning push protection, vulture/knip baselines | `.github/workflows/nightly.yml`, `.github/dependabot.yml`, settings | the first nightly run produces a report (the first issues to file: the 64 logic survivors in `secret_store.py` listed in §1.4); Windows job green for two weeks, then required | low (nightly does not block) | 1, 2. INV (workflows) |

Not included on purpose: any product feature; rewriting the frontend; replacing LangChain.

---

## 9. Open decisions for the maintainer

1. **Move the repository to a (free) GitHub organization?** Merge queue (safe "selected tests
   on PRs, full suite before merge") and team-based `CODEOWNERS` need an organization.
   *Recommend yes, before the second human joins*, since it changes URLs once.
2. **Accept 0007** (second human, code-owner review on invariant paths). *Recommend accept as
   written*, plus: code-owner review also on `quality/baseline.json`, `tests/tool_schemas.txt`,
   import contracts and `.github/`.
3. **Who may loosen a ratchet or add an import-contract exception?** *Recommend: only a human,
   through CODEOWNERS, with a one-line reason in the PR.* This is the one rule that keeps the
   floor from sinking.
4. **A second model family in review** (Codex review) for invariant paths: costs money and sends
   diffs to a second vendor. *Recommend yes for invariant paths only*, measured by the
   seeded-bug recall of §5 for a month before extending it.
5. **A 2–3 week structure period** with feature work paused while steps 1–11 land, with
   freezes per component. *Recommend yes*: the splits are cheap now and expensive at 3× the
   size, and parallel feature work on `presentations.py` or `session.py` during the splits
   would conflict.
6. **Is 1M lines of *core* the goal?** *Recommend a budget for the core* (runtime, conversation,
   web, approvals, secrets: for example ≤ 100k lines) and let growth happen in components
   behind fixed interfaces (office formats, connectors, skills, workflows), where a mistake is
   contained. The guardrails above matter most where a mistake is not contained.
7. **Real-machine ownership**: who runs the weekly Windows checklist, and whether to add a
   self-hosted Windows runner or VM with Office installed (the only way to automate "does
   PowerPoint open this file"). *Recommend: the second human owns the checklist; decide on the
   runner after a month of the checklist shows how often it catches something.*

---

## Appendix: how the numbers were measured

Scripts are in this scratchpad (`scripts/`): `funcs.py` (AST function length and branch count;
nested functions are counted inside their parents too), `graph.py` (grimp: package fan-in/out,
module fan-out, upstream closure, cycles), `sample.py` (random test sampling; seeds 7 and 31),
`stale_refs.py` (path references). Coverage: pytest-cov 7.1 / coverage 7.16 installed into a
scratch directory, full suite, branch mode (`cov.json`, `cov.txt`). Mutation: mutmut 3.8.0 on a
scratch copy (`mut/`), results in `mutmut2-results.txt` and `logic_survivors.txt`. xdist: full
suite with `-n 4` (`xdist.log`). Token counts are bytes/4. PR and CI data from the GitHub REST
API (`/pulls`, `/actions/runs`, `/rulesets`), 66 PRs (#1 opened 2026-10-05) and the last 58 CI
runs. Vendor facts verified today: mutmut 3.8.0 (PyPI, needs `fork`), pytest-testmon 2.2.0,
import-linter 2.15 contract types (installed source), GitHub-hosted runner specs and free Actions
for public repositories (docs.github.com), merge queue availability (GitHub changelog
2023-07-12), ruleset rule types (docs.github.com), Codex GitHub review (developers.openai.com),
Claude Code `CLAUDE.md`/`AGENTS.md` loading rules (code.claude.com), TypeScript 6 strict default
(local probe with tsc 6.0.3). Versions of other tools from PyPI/npm on 2026-10-11.
