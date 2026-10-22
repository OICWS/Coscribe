# Design note: "Run in background" for a running command (#510) (2026-10-22)

Design before code: the change crosses the tools, the runtime, the session, the chat socket and the UI, and one choice (how a live process is handed over) shapes the rest. Status: **for the maintainer's decision**; nothing is built.

## 摘要（中文）
- 现在一个正在跑的命令（`run_python_script`、`run_node_script`）只能等它结束或超时，停止会连整轮对话一起停。要的是命令行上的 **Run in background** 按钮：按下后这次工具调用立刻返回，模型继续下一步，命令作为后台任务接着跑，跑完像别的后台任务一样回到对话。
- 办法：这两个工具不再用 `subprocess.run` 等到底，而是自己启动进程、把输出写进文件；按钮通过聊天 socket 发一个 `detach_command`，工具调用就地返回 `task_id`，一个线程接手监督进程、写后台任务记录、结束时通知对话。不改任何工具的 schema（决定 0001）。
- 请你决定的三件事在最后。

## What exists
- `run_python_script` / `run_node_script` (`tools/exec/`): `subprocess.run(capture_output=True, timeout=...)` in the tool's worker thread (default 120 s, at most 600 s). The result has `stdout` and `stderr` apart, `exit_code`, `timed_out` and the files written.
- Background tasks (`tools/bookkeeping/background_tasks.py`): an asyncio subprocess whose combined output goes to a log file, a supervising coroutine that settles the record (`succeeded`, `failed`, `timed_out`, `killed`) and calls `_announce`, which refreshes the panel and, through the inbox, tells the conversation. Lost on a server restart, said plainly in its own docstring.
- The chat UI already knows which tool rows are still running (`isRunning` in `ToolRuns.tsx`).

## Proposed mechanism
1. **The two script tools start the process themselves** (`Popen`, own process group on POSIX as the background shell already does) and pump stdout and stderr into two files in the scratch directory. When it ends they read the files and return the same dict as today, so nothing changes for a command that is not detached.
2. **A registry of running commands keyed by the tool call's id.** A tool function does not know its call id (the schema is fixed), so a small middleware sets a context variable to `request.tool_call["id"]` before the tool runs; a sync tool runs in a worker thread that inherits it. The tool registers `{process, detach flag}` under that id while it waits.
3. **`detach_command {id}` on the chat socket** (`wire.py` first, types regenerated). The session finds the entry and sets the flag. The waiting tool wakes, creates a `BackgroundTask` record (same store, so it shows in the Background tasks panel and can be stopped and read), copies the output so far into its log, and returns `{"status": "running_in_background", "task_id": ..., "output_so_far": ...}` to the model at once.
4. **A watcher thread** keeps pumping the process into the log, waits for exit, settles the record and announces it with `loop.call_soon_threadsafe` (the listener is written for the event loop). The conversation is told as for any finished background task.
5. **The UI**: a running row of one of these two tools shows **Run in background**; any other running tool shows no button. After the click the row settles with the tool's result, and the task is in the panel.

## Constraints kept
- No tool schema change; the detach is a client action, not a model-visible tool (0001).
- Approvals and the folder guard are untouched: the same process, started the same way, was approved as it was.
- No sandbox claim: the process runs as the user, as before.
- Stop still stops the turn and the process, detached or not (a detached one is stopped from the panel).

## Cost and pull requests
About 450 lines in two PRs: (1) the runner, the registry, the middleware, the socket message and the session handler, with tests that run a real short process and detach it; (2) the button and a Playwright spec against the stub model. Hot files: `conversation/session.py`, `conversation/wire.py`, `tools/exec/`, `tools/bookkeeping/background_tasks.py`, `ToolRuns.tsx`. Neither PR touches an invariant path.

## Not verified
- That a worker thread of the tool node really inherits the context variable on this LangGraph version: PR 1 starts by proving it with a test; if it does not, the middleware passes the id another way.
- Windows: killing a process group and the pump threads need a run on the packaged app.

## Questions for the maintainer
1. **Scope.** Only the two script tools (the commands the model runs through coscribe), not Codex tasks, connector calls or the background-script tools themselves? Recommended: yes.
2. **After detaching, how long may it run?** The foreground limit was 600 s at most; the background tool allows 30 minutes by default and 6 hours at most. Recommended: the background default of 30 minutes, since the person chose to let it go on.
3. **Output order.** stdout and stderr are kept apart in a foreground result but are one stream in a background log. Recommended: after a detach, one log in the order it was written, and `output_so_far` in the result as that log's tail.
