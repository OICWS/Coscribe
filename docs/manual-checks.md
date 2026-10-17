# Checks only a person can do (2026-10-17)

The 20 checks of issue #393, after a second try at scripting each. Eight have a part that now
runs on a Windows runner and fails when the thing breaks; every check still has a part that needs
a real machine, an account or Office, and that part is written below as steps you can do in the
time given. Tick the check on #393 and say what you saw; a failure becomes its own issue.

Scripted parts run in `.github/workflows/windows-more-checks.yml` (`real-windows`, the tests in
`office-agent/tests/test_windows_real.py`; `codeowners`), nightly and on a pull request that
changes it. The existing jobs stay: `windows.yml` (the whole pytest suite, nightly) and
`windows-checks.yml` (the repository's scripts).

Each scripted test was shown to fail when its thing breaks (PR #408, closed). On the Windows
runner four changes were made on purpose: taskkill without `/T`, the keychain store returning the
plaintext, the Python lookup ignoring a broken stub, `Format-Hex` taken out of the read list; 5
of the 8 tests went red, each the one that covers the change. The no-Node message was broken the
same way on Linux. A CODEOWNERS file with an unknown owner made the API list an error. The hook
and YaHei tests were not broken.

| # | Check | Scripted now | Left for you | Time |
|---|---|---|---|---|
| 1 | First launch and a real chat | nothing | all | 20 min |
| 2 | Credential Manager, locked keychain | yes, in part | the Settings > Secrets screen | 3 min |
| 3 | A hosted connector with a key | nothing | all | 15 min |
| 4 | Store stub, conda-only Python | a stub in front of Python | a real stub, conda | 10 min |
| 5 | Codex on Windows | `Format-Hex` on the real PowerShell | a live Codex run | 10 min |
| 6 | Background commands | tree kill with taskkill | the notice from a model turn | 5 min |
| 7 | Window frame | nothing | all | 10 min |
| 8 | Fonts and layout | font table (nightly, existing) | the looks | 10 min |
| 9 | Conversations messaging | nothing | all | 5 min |
| 10 | Real providers | nothing | all | 10 min |
| 11 | MCP tool returning an artifact | nothing | all | 5 min |
| 12 | Conversion through Office or WPS | nothing | all | 10 min |
| 13 | Word documents in Word | nothing | all | 15 min |
| 14 | Word viewer panel | nothing | all | 5 min |
| 15 | Workbooks in Excel | nothing | all | 15 min |
| 16 | IronCalc and resvg, packaged | YaHei drawn by resvg | the installer build | 10 min |
| 17 | Decks in PowerPoint | nothing | all | 30 min |
| 18 | Browser tools on a real page | missing Node says so | the page | 5 min |
| 19 | Codeowners errors | yes | nothing | 0 |
| 20 | A second person follows the start guide | nothing | all | 60 min |

Why the others cannot run on a runner: a GitHub Windows runner has no Word, Excel, PowerPoint or
WPS (and no way to install them in minutes), no desktop session for the Electron window frame, no
model key or connector account (a key as a repository secret would be a settings change only the
maintainer makes), and only one fixed font set.

## 1. First launch and a real chat in the desktop app (20 min)
1. Install the newest desktop build on a Windows profile that never ran coscribe. Start it.
   Expected: the setup page asks for a model and a key; after saving it you land in a chat.
2. Ask: "List the files in my workspace, read the biggest one and summarise it." While it runs
   tools, press Stop. Expected: the turn stops within a few seconds and the composer is usable.
3. Ask for something that needs approval (for example, write a file). Expected: an approval
   card; Allow runs it, Deny tells the model.
4. Ask again for a write, and reload the window (Ctrl+R) while the card is open. Expected: the
   card is still there after the reload; resolve it, the turn continues.
5. Create a scheduled task for 2 minutes from now that needs approval. Reload while it is open,
   resolve it afterwards. Expected: the same.
6. Wait for the task to fire at its time. Expected: it runs once, its thread appears in the
   sidebar. Open the Chat, Connectors and Skills tabs and the thread sidebar once each:
   no error banner, no blank tab.

## 2. Windows Credential Manager and a locked keychain (3 min)
Scripted: save, read back from a new process, find the entry with `cmdkey /list`, remove it
behind the app's back (the error says "re-enter it via Settings"), and a hook under cmd and
under PowerShell.
By hand:
1. Settings > Secrets: add a secret named `check-1` with value `abc`. Open Windows Credential
   Manager (Start, type "Credential Manager", Windows Credentials). Expected: an entry whose name
   contains `coscribe` and the secret's reference appears.
2. Delete that entry in Credential Manager, then open Settings > Connectors and a connector that
   used it. Expected: the connector shows "Secret problem"; the app does not crash, the other
   connectors still load.

## 3. A hosted connector, signed in and with a key (15 min)
1. Settings > Connectors: add one hosted connector (for example Notion). Expected: the browser
   opens once, you sign in, the app shows it connected. Restart the app: still connected, no
   second browser window.
2. In a chat ask it to use one tool of that connector. Expected: the call succeeds.
3. Add a remote connector by URL; in the add dialog fill a header with the secret picker's
   placeholder, the value being saved in Settings > Secrets. Expected: it connects, and
   the value does not appear in the chat or the tool result.
4. In a chat of 10 or more turns, open the usage line after the third turn. Expected: cached
   tokens are above 0 on each later turn.

## 4. Python on Windows: the Store stub and a conda-only Python (10 min)
Scripted: a `python.cmd` that exits 9009 in front of the real Python on PATH is replaced by a
working interpreter.
By hand, on a machine where the only `python` is the Store alias (Settings > Apps > Advanced app
settings > App execution aliases: leave `python.exe` on and uninstall Python):
1. Settings > Connectors: add a stdio connector with command `python` and any script.
   Expected: the connector shows a message that says Python is missing or which one to pick, not
   an endless spinner or only "Connection closed"; Settings > Environment lists no interpreter.
2. Repeat on a machine with Python only through conda (Anaconda Prompt, nothing on the system
   PATH). Expected: the same message, and picking the conda `python.exe` in Settings >
   Environment makes the connector start.

## 5. Codex and the code module on Windows (10 min)
Scripted: the real Windows PowerShell 5.1 runs `Format-Hex -LiteralPath` (it has no `-Count`; that
was added in 6.1) and returns the bytes as text, and the code module counts it as a read.
By hand:
1. Open a code thread on a folder with a binary file. Ask Codex to show the first bytes of it with
   Format-Hex. Expected: no approval card (it is a read), the hex table in the answer is not
   garbled.
2. Run the "Verify by hand" list on the code-runtime card
   (`office-agent/src/coscribe/code_runtime/AGENTS.md`): first-use download, a PowerShell command
   and an edit with an approval card for each, "allow" in Settings > Code, the shared server
   stopping when idle.

## 6. Background commands on Windows (5 min)
Scripted: a command that starts a child process is stopped with taskkill, and the child is gone.
By hand:
1. Ask the model to start a script that sleeps 60 seconds in the background. Expected: the
   background panel shows it Running; a notice appears in the browser tab or tray; after 60
   seconds it shows Finished.
2. Start it again and press Stop in the panel. Expected: Killed within a few seconds; in Task
   Manager no `python.exe` or `cmd.exe` of that script is left.

## 7. The window frame: title bar, dialogs and panel docking (10 min)
1. Open any dialog (Settings). Drag the window by the title bar. Expected: the window moves, the
   close, minimise and maximise buttons sit in the title bar in the theme's colour, nothing is
   covered by the dialog's backdrop.
2. Open the Environment dialog and press Win+Shift+S (or PrtScn). Expected: the screenshot tool
   opens over the dialog; the dialog stays.
3. Drag a panel to the left column, then to the dock. Expected: while dragging a picture of the
   browser view stands in; on drop the real view follows the panel.
4. Choose Ultra in the effort control, in the light and the dark theme. Expected: the wave
   animation plays and does not flicker or clip.

## 8. Fonts and layout on Windows (10 min)
Scripted already: the nightly job measures the Windows fonts and the committed table must equal
them.
By hand:
1. Settings > General: set the interface font to Figtree, then to OpenDyslexic; at the smallest and the
   largest size open the denser panels (Outputs, Context, Background). Expected: no text cut off.
2. Make the approval panel 460 px wide and open an approval card; narrow the window and open the
   messaging dialog. Expected: buttons and text wrap, nothing overlaps.
3. Look at the composer's plus button at 90 % and 125 % font size. Expected: aligned with the
   input box.
4. On a Windows with DengXian, SimHei, KaiTi and FangSong installed, run in `office-agent/`:
   `python scripts/measure_font_advances.py "C:/Windows/Fonts"`. Expected: no font reported
   missing; if the table differs, commit it.

## 9. Conversations messaging each other, with a real model (5 min)
1. Open two conversations A and B; turn messaging on for both. In A: "Send B a note saying
   hello, with send_to_conversation." Expected: A finds the tool through search, calls it; B
   shows the note and can answer.

## 10. Real providers (10 min)
1. Settings > Providers: add a Gemini key. Expected: the model list loads. Set an effort level
   and send one message; the request log shows the effort.
2. Send one request each to Claude and OpenAI with a non-default effort. Expected: both answer.

## 11. MCP tool that returns an artifact (5 min)
1. Connect an MCP server whose tool returns an artifact, and call it from a chat. Expected: the
   artifact opens; search its text for the secret you gave the connector: it is not there.

## 12. File conversion and preview through Microsoft Office or WPS (10 min)
1. On a machine with WPS Office and nothing in Word: `cd office-agent && python
   scripts/check_office.py --require`. Expected: every row passes (it passed with Microsoft Office
   on 2026-10-16).
2. In the app convert a .doc, .xls, .ppt to their new formats and each of the six types to PDF.
   Expected: each output opens. Open a preview while the same file is open in Word. Expected: the
   file in Word stays open and unchanged.

## 13. Word documents opened in Word (15 min)
1. Have the app edit a document with comments, tracked changes, a table and a table of contents,
   then open it in Word. Expected: comment threads and resolved state, the table's header and
   total row styling, the page number field and the TOC (press F9 to refresh) are right; no
   "unreadable content" prompt.
2. Chinese headings use Microsoft YaHei; the comment author is the Windows user name.
3. Open a real Word-made file that has `commentsIds.xml` and `people.xml` (any file with
   threaded comments), have the app edit it, reopen in Word. Expected: opens without a repair
   prompt, comments intact.

## 14. The Word viewer panel on Windows (5 min)
1. In the app open a Word file with tables, pictures, sections, a long text and a font the
   machine lacks. Expected: layout close to Word; note the render time of the long one
   (under 10 seconds is fine).

## 15. Workbooks opened in Excel (15 min)
1. Open the evaluation workbooks and a file saved without cached values in Excel, then in
   Explorer's preview pane and in Outlook's. Expected: values show, charts look right, column
   widths fit the content.
2. Open the 5,000-row workbook and task 11's copy; data labels on the charts are readable.
3. Ask the app to edit a workbook with a pivot table, a slicer and a form control. Expected: the
   guard refuses or keeps them; Excel opens the result without repair.

## 16. IronCalc and resvg in the packaged Windows build (10 min)
Scripted: resvg draws Chinese text with the installed Microsoft YaHei (the font file is there and
the picture has ink). The nightly pytest runs both modules from a source install.
By hand, from the installer build:
1. Ask for a workbook with formulas to be recalculated. Expected: values appear, no "No module
   named ironcalc".
2. Ask for a deck with a Chinese title and preview a page. Expected: the page draws, Chinese in
   YaHei, no "No module named resvg_py".
3. Recalculate a workbook using a function IronCalc lacks (for example a recent dynamic-array
   function). Expected: only `#NAME?` is flagged; compare a few results with Excel.

## 17. Decks opened in PowerPoint (30 min)
1. Build one new deck in the app; note the time.
2. Open in PowerPoint: a deck with SmartArt, shadow and a filled template; a deck on your own
   template whose master has pictures; native charts; icons; the redesigned deck; ppt-master's
   side-by-side decks. Expected: each opens without repair and looks as on the preview.
3. Play a deck with audio (the sound plays). Edit a deck that has groups made in PowerPoint, by
   shape path. Expected: edits land on the right shape.
4. On a few pages compare the app's overflow check with PowerPoint's line breaks. Expected: no
   page flagged as fine that overflows.

## 18. Browser tools on a real page (5 min)
Scripted: with no Node on PATH the error says Node.js is missing and where to get it.
By hand:
1. In the desktop app ask the model to open a real web page, read it and click a link.
   Expected: the browser panel shows the page, the link opens, the answer quotes the page.
2. On a machine with neither Python nor Node on PATH, ask for a script. Expected: the message
   says which is missing.

## 19. Repository settings only an admin can check (0 min)
Scripted: the `codeowners` job asks GitHub for the CODEOWNERS errors of the branch and fails when
there are any. Nothing to do by hand.

## 20. A second person follows the start guide (60 min)
1. Someone who did not write `docs/start-guide.md` follows it from a clean machine with a new
   clone, up to a draft pull request. Expected: they reach it; write down each step where they
   stopped or guessed, and open an issue per step.
