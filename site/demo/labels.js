var CoscribeLabels = (function(exports) {
	Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
	// src/lib/transcriptGrouping.ts
	function str(args, key) {
		const value = args[key];
		return typeof value === "string" && value ? value : void 0;
	}
	/** ask_user_question's first question; an older call asked one directly. */
	function firstQuestion(args) {
		const questions = args.questions;
		if (!Array.isArray(questions)) return str(args, "question");
		const first = questions[0];
		const text = first && typeof first === "object" ? first.question : void 0;
		if (typeof text !== "string" || !text) return void 0;
		return questions.length > 1 ? `${text} (+${questions.length - 1} more)` : text;
	}
	function basename(path) {
		return path.split(/[/\\]/).pop() || path;
	}
	function fileArg(args) {
		const path = str(args, "path") ?? str(args, "file_path");
		return path ? basename(path) : void 0;
	}
	/** The one generic, works-for-every-tool failure signal this app has --
	* straight off the checkpointed ToolMessage's own `.status` field (see
	* wire.ts's ToolResultEvent/HistoryEntry, set server-side by agent.py's
	* _CatchToolErrorsMiddleware whenever the tool's Python body raised).
	* Deliberately NOT inferred by sniffing each tool's own result shape
	* (e.g. a command's exit_code) -- that would only cover the tools this
	* file happens to special-case, where this covers all of them, including
	* a failed write_file/edit_file/read_file. `undefined` (not yet resolved,
	* or a denied approval that never ran) reads as "not a failure", same as
	* a still-pending item. */
	function isFailure(item) {
		return item.isError === true;
	}
	/** run_python_script/run_node_script are the two tools a user would call
	* "running a command" in the Claude-Code-web sense the reference UI this
	* matches uses -- run_background_script/check_background_task have their
	* own distinct "started"/"checked" semantics and aren't folded in here. */
	const COMMAND_TOOL_NAMES = /* @__PURE__ */ new Set([
		"run_python_script",
		"run_node_script",
		"run_code_command"
	]);
	/** Exact-name handlers for the common built-in tools -- gives Claude-Code-
	* style specificity ("Wrote deck.pptx", "Ran a command") for the tools a
	* user actually sees most. Anything not listed here (a less common
	* built-in, or a dynamically-named MCP connector tool like
	* "playwright_browser_navigate") falls through to summarizeToolNameParts's
	* generic prefix table below, not a hardcoded entry for all ~35+ tools. */
	const TOOL_SUMMARIES = {
		run_python_script: (a) => ({
			verb: "Ran a command",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		run_node_script: (a) => ({
			verb: "Ran a command",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		run_background_script: (a) => ({
			verb: "Started a background script",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		run_background_command: (a) => ({
			verb: "Started a background command",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		check_background_task: () => ({
			verb: "Checked a background task",
			object: null
		}),
		kill_background_task: () => ({
			verb: "Killed a background task",
			object: null
		}),
		wake_on_task: (a) => ({
			verb: "Waiting on a background task",
			object: str(a, "reason") ?? null,
			glue: ": "
		}),
		write_docx: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a document"
		}),
		write_pdf: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a PDF"
		}),
		write_xlsx: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a spreadsheet"
		}),
		write_xlsx_cells: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a spreadsheet"
		}),
		modify_xlsx: (a) => ({
			verb: "Changed",
			object: fileArg(a) ?? "a spreadsheet"
		}),
		write_pptx: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a deck"
		}),
		write_file: (a) => ({
			verb: "Wrote",
			object: fileArg(a) ?? "a file"
		}),
		edit_file: (a) => ({
			verb: "Edited",
			object: fileArg(a) ?? "a file"
		}),
		edit_file_batch: (a) => ({
			verb: "Edited",
			object: fileArg(a) ?? "a file"
		}),
		read_docx: (a) => ({
			verb: "Read",
			object: fileArg(a) ?? "a document"
		}),
		read_pdf: (a) => ({
			verb: "Read",
			object: fileArg(a) ?? "a PDF"
		}),
		read_xlsx: (a) => ({
			verb: "Read",
			object: fileArg(a) ?? "a spreadsheet"
		}),
		read_pptx: (a) => ({
			verb: "Read",
			object: fileArg(a) ?? "a deck"
		}),
		read_file: (a) => ({
			verb: "Read",
			object: fileArg(a) ?? "a file"
		}),
		list_files: (a) => {
			const path = str(a, "path");
			return path && path !== "." ? {
				verb: "Listed",
				object: basename(path)
			} : {
				verb: "Listed files",
				object: null
			};
		},
		search_files: (a) => ({
			verb: "Searched files",
			object: str(a, "query") ?? null,
			glue: ": "
		}),
		search_pdf: (a) => ({
			verb: "Searched PDF",
			object: str(a, "query") ?? null,
			glue: ": "
		}),
		search_images: (a) => ({
			verb: "Searched images",
			object: str(a, "query") ?? null,
			glue: ": "
		}),
		web_search: (a) => ({
			verb: "Searched the web",
			object: str(a, "query") ?? null,
			glue: ": "
		}),
		download_image: (a) => ({
			verb: "Downloaded",
			object: fileArg(a) ?? "an image"
		}),
		save_connector_file: () => ({
			verb: "Downloaded",
			object: "a connector file"
		}),
		set_pptx_background_image: () => ({
			verb: "Set a slide background image",
			object: null
		}),
		add_pptx_scrim: () => ({
			verb: "Added a text-legibility overlay",
			object: null
		}),
		add_pptx_chart: () => ({
			verb: "Added a chart",
			object: null
		}),
		add_pptx_image: () => ({
			verb: "Added an image",
			object: null
		}),
		add_xlsx_chart: () => ({
			verb: "Added a chart",
			object: null
		}),
		add_docx_chart: () => ({
			verb: "Added a chart",
			object: null
		}),
		add_docx_image: () => ({
			verb: "Added an image",
			object: null
		}),
		format_xlsx_cells: () => ({
			verb: "Formatted cells",
			object: null
		}),
		recalc_xlsx: (a) => ({
			verb: "Recalculated",
			object: fileArg(a) ?? "a spreadsheet"
		}),
		task_create: (a) => ({
			verb: "Added a task",
			object: str(a, "content") ?? null,
			glue: ": "
		}),
		task_update: () => ({
			verb: "Updated a task",
			object: null
		}),
		task_list: () => ({
			verb: "Listed tasks",
			object: null
		}),
		remember: () => ({
			verb: "Saved a memory",
			object: null
		}),
		ask_user_question: (a) => ({
			verb: "Asked",
			object: firstQuestion(a) ?? "a question",
			glue: ": "
		}),
		install_package: (a) => ({
			verb: "Asked to install",
			object: str(a, "package") ?? "a package"
		}),
		spawn_agent: (a) => ({
			verb: "Delegated to a sub-agent",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		run_code_task: (a) => ({
			verb: "Handed a coding task to the code module",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		run_code_command: (a) => ({
			verb: "Ran a command",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		apply_code_change: (a) => {
			const paths = Array.isArray(a.paths) ? a.paths.filter((p) => typeof p === "string") : [];
			return paths.length > 0 ? {
				verb: "Changed",
				object: paths.map(basename).join(", ")
			} : {
				verb: "Changed files",
				object: null
			};
		},
		spawn_agent_background: (a) => ({
			verb: "Started a sub-agent",
			object: str(a, "description") ?? null,
			glue: ": "
		}),
		get_file_info: (a) => ({
			verb: "Checked",
			object: fileArg(a) ?? "a file"
		}),
		sleep_until: () => ({
			verb: "Scheduled a wake-up",
			object: null
		}),
		sleep_for: () => ({
			verb: "Scheduled a wake-up",
			object: null
		}),
		wake_on_subagent: () => ({
			verb: "Set to resume when the sub-agent finishes",
			object: null
		}),
		wake_on_event: (a) => ({
			verb: "Set to resume on",
			object: str(a, "event_key") ?? "an event"
		}),
		signal_event: (a) => ({
			verb: "Signaled",
			object: str(a, "event_key") ?? "an event"
		}),
		check_subagent_task: () => ({
			verb: "Checked on a sub-agent",
			object: null
		}),
		list_subagent_tasks: () => ({
			verb: "Listed sub-agents",
			object: null
		}),
		stop_subagent: () => ({
			verb: "Stopped a sub-agent",
			object: null
		}),
		review_work: () => ({
			verb: "Asked a reviewer to check the work",
			object: null
		}),
		load_skill: (a) => ({
			verb: "Loaded skill",
			object: str(a, "name") ?? null
		}),
		draft_workflow: () => ({
			verb: "Drafted a workflow",
			object: null
		}),
		find_connector: (a) => ({
			verb: "Looked for a connector",
			object: str(a, "need") ?? null,
			glue: ": "
		}),
		revise_workflow: () => ({
			verb: "Revised a workflow",
			object: null
		}),
		test_workflow: () => ({
			verb: "Tested a workflow",
			object: null
		}),
		edit_scheduled_task: () => ({
			verb: "Proposed changes to a task",
			object: null
		}),
		search_tools: (a) => ({
			verb: "Searched tools",
			object: str(a, "query") ?? null,
			glue: ": "
		}),
		read_web_page: (a) => ({
			verb: "Read",
			object: str(a, "url") ?? "a web page"
		})
	};
	const PREFIX_VERBS = [
		["write_", "Wrote"],
		["read_", "Read"],
		["search_", "Searched"],
		["download_", "Downloaded"],
		["list_", "Listed"],
		["add_", "Added"],
		["set_", "Updated"],
		["delete_", "Deleted"],
		["remove_", "Removed"],
		["install_", "Installed"],
		["uninstall_", "Uninstalled"],
		["create_", "Created"],
		["update_", "Updated"],
		["run_", "Ran"]
	];
	/** Generic fallback for any tool not in TOOL_SUMMARIES -- a small prefix
	* table (covers most naming conventions used across this codebase's
	* ~35+ built-ins) plus a safe last resort: the bare tool name, with no
	* object to emphasize. Also handles MCP connector tools, whose names are
	* dynamic (server-provided) and can't be enumerated ahead of time. */
	function summarizeToolNameParts(toolName, args) {
		for (const [prefix, verb] of PREFIX_VERBS) if (toolName.startsWith(prefix)) {
			const object = fileArg(args) ?? str(args, "query") ?? str(args, "name");
			if (object) return {
				verb,
				object
			};
			return {
				verb: `${verb} ${toolName.slice(prefix.length).replace(/_/g, " ")}`,
				object: null
			};
		}
		return {
			verb: toolName,
			object: null
		};
	}
	const PRESENT_TENSE = {
		Wrote: "Writing",
		Read: "Reading",
		Edited: "Editing",
		Listed: "Listing",
		Searched: "Searching",
		Downloaded: "Downloading",
		Added: "Adding",
		Updated: "Updating",
		Deleted: "Deleting",
		Removed: "Removing",
		Installed: "Installing",
		Uninstalled: "Uninstalling",
		Created: "Creating",
		Ran: "Running",
		Started: "Starting",
		Checked: "Checking",
		Killed: "Stopping",
		Formatted: "Formatting",
		Recalculated: "Recalculating",
		Saved: "Saving",
		Asked: "Asking",
		Delegated: "Delegating",
		Loaded: "Loading",
		Set: "Setting",
		Tested: "Testing",
		Opened: "Opening",
		Fetched: "Fetching",
		Drafted: "Drafting",
		Revised: "Revising",
		Proposed: "Proposing"
	};
	/** "Wrote" -> "Writing"; a verb with no known present form stays as is. */
	function presentTense(verb) {
		const space = verb.indexOf(" ");
		const first = space === -1 ? verb : verb.slice(0, space);
		const present = PRESENT_TENSE[first];
		return present ? present + verb.slice(first.length) : verb;
	}
	const BASE_FORM = {
		Wrote: "Write",
		Read: "Read",
		Edited: "Edit",
		Listed: "List",
		Searched: "Search",
		Downloaded: "Download",
		Added: "Add",
		Updated: "Update",
		Deleted: "Delete",
		Removed: "Remove",
		Installed: "Install",
		Uninstalled: "Uninstall",
		Created: "Create",
		Ran: "Run",
		Started: "Start",
		Checked: "Check",
		Killed: "Stop",
		Formatted: "Format",
		Recalculated: "Recalculate",
		Saved: "Save",
		Asked: "Ask",
		Delegated: "Delegate",
		Loaded: "Load",
		Set: "Set",
		Tested: "Test",
		Opened: "Open",
		Fetched: "Fetch",
		Drafted: "Draft",
		Revised: "Revise",
		Proposed: "Propose",
		Used: "Use",
		Handed: "Hand",
		Moved: "Move",
		Copied: "Copy",
		Renamed: "Rename",
		Sent: "Send",
		Applied: "Apply",
		Converted: "Convert",
		Replaced: "Replace"
	};
	/** "Ran a command" -> "Run a command", for a call still waiting to be approved; a verb with no
	* known base form stays as is. */
	function baseForm(verb) {
		const space = verb.indexOf(" ");
		const first = space === -1 ? verb : verb.slice(0, space);
		const base = BASE_FORM[first];
		return base ? base + verb.slice(first.length) : verb;
	}
	/** A call counts as running while a live turn hasn't returned its result;
	* a denied or still-pending approval never ran. */
	function isRunning(item, live) {
		if (!live || item.result !== void 0 || item.isError !== void 0) return false;
		return item.kind === "tool" || item.status === "approved";
	}
	function partsFor(item, running = false) {
		const summarized = TOOL_SUMMARIES[item.toolName]?.(item.arguments) ?? summarizeToolNameParts(item.toolName, item.arguments);
		const base = running ? {
			...summarized,
			verb: presentTense(summarized.verb),
			running: true,
			shimmer: true
		} : summarized;
		let parts = item.kind === "approval" && item.status === "pending" ? {
			...base,
			verb: baseForm(base.verb)
		} : base;
		if (isFailure(item)) parts = {
			...parts,
			verb: COMMAND_TOOL_NAMES.has(item.toolName) ? "Failed to run" : parts.verb,
			failed: true
		};
		return parts;
	}
	/** Structured form -- verb plus an optional emphasized object -- for a
	* caller (ToolCallRow's collapsed label, a ToolRunGroup's header) that
	* wants to render the object as a distinct inline chip rather than plain
	* text. */
	function summarizeItemParts(item, running = false) {
		return partsFor(item, running);
	}
	const SUMMARY_CAP = 3;
	const SUBAGENT_TOOL_NAMES = /* @__PURE__ */ new Set([
		"spawn_agent",
		"review_work",
		"run_code_task"
	]);
	const FETCH_TOOL_NAMES = /* @__PURE__ */ new Set([
		"read_web_page",
		"download_image",
		"browser_navigate"
	]);
	const OFFICE_FILE = /_(docx|pptx|xlsx)(_|$)/;
	const NOT_AN_EDIT = /^(read|write|list|check|render|extract)_/;
	function categoryOf(toolName, connectorTools) {
		if (connectorTools.has(toolName)) return "connector";
		if (COMMAND_TOOL_NAMES.has(toolName) || toolName === "run_background_script" || toolName === "run_background_command") return "command";
		if (SUBAGENT_TOOL_NAMES.has(toolName)) return "subagent";
		if (FETCH_TOOL_NAMES.has(toolName)) return "fetch";
		if (toolName === "web_search" || toolName.startsWith("search_") && toolName !== "search_tools") return "search";
		if (toolName.startsWith("write_") || toolName === "convert_office_file") return "write";
		if (toolName === "edit_file" || toolName === "edit_file_batch" || toolName === "apply_code_change") return "edit";
		if (OFFICE_FILE.test(toolName) && !NOT_AN_EDIT.test(toolName)) return "edit";
		if (toolName === "list_files" || toolName === "get_file_info") return "read";
		if (toolName.startsWith("read_") && toolName !== "read_skill_file") return "read";
		return "other";
	}
	/** Past and present verb, and the noun counted, for each category's
	* clause ("Ran 3 commands" / "Running 3 commands"). */
	const CATEGORY_WORDS = {
		command: [
			"Ran",
			"Running",
			"command"
		],
		write: [
			"Wrote",
			"Writing",
			"file"
		],
		edit: [
			"Edited",
			"Editing",
			"file"
		],
		read: [
			"Read",
			"Reading",
			"file"
		],
		search: [
			"Searched",
			"Searching",
			"time"
		],
		fetch: [
			"Fetched",
			"Fetching",
			"page"
		],
		subagent: [
			"Finished",
			"Running",
			"sub-agent task"
		],
		connector: [
			"Used",
			"Using",
			"tool"
		]
	};
	const FILE_CATEGORIES = /* @__PURE__ */ new Set([
		"write",
		"edit",
		"read"
	]);
	/** The files a call touched: its path, or the code module's list of them. */
	function filePathsArg(args) {
		const path = str(args, "path") ?? str(args, "file_path");
		if (path) return [path];
		return Array.isArray(args.paths) ? args.paths.filter((p) => typeof p === "string" && p !== "") : [];
	}
	function categoryClause(category, items, live) {
		if (items.length === 1) return partsFor(items[0], isRunning(items[0], live));
		const [past, present, noun] = CATEGORY_WORDS[category];
		const running = items.some((item) => isRunning(item, live));
		const failedCount = items.filter(isFailure).length;
		let count = items.length;
		let onlyFile;
		if (FILE_CATEGORIES.has(category)) {
			const keys = items.flatMap((item, index) => {
				const paths = filePathsArg(item.arguments);
				return paths.length > 0 ? paths : [`#${index}`];
			});
			count = new Set(keys).size;
			if (count === 1 && !keys[0].startsWith("#")) onlyFile = basename(keys[0]);
		}
		const verb = running ? present : past;
		const counted = `${verb} ${count} ${count === 1 ? noun : `${noun}s`}`;
		return {
			verb: onlyFile ? verb : counted,
			object: onlyFile ?? null,
			...failedCount > 0 && { failedCount },
			...running && {
				running: true,
				shimmer: true
			}
		};
	}
	/** Structured headline for a ToolRunGroup's collapsed header: one clause
	* per kind of work, in the order each first happened -- "Ran 117 commands
	* (2 failed), wrote 4 files, read 5 files, and 9 more actions". A kind
	* done once keeps the call's own wording ("Wrote `deck.pptx`"). Calls that
	* fit no kind, and kinds past the cap, are counted in `more`; a run made
	* only of such calls is listed call by call instead. The expanded list
	* (ToolRunGroupView) still shows every call. */
	function summarizeGroupParts(items, live = false, connectorTools = /* @__PURE__ */ new Set()) {
		const last = items[items.length - 1];
		const active = last && isRunning(last, live) ? partsFor(last, true) : null;
		if (active) items = items.slice(0, -1);
		const byCategory = /* @__PURE__ */ new Map();
		for (const item of items) {
			const category = categoryOf(item.toolName, connectorTools);
			const bucket = byCategory.get(category);
			if (bucket) bucket.push(item);
			else byCategory.set(category, [item]);
		}
		const others = byCategory.get("other") ?? [];
		byCategory.delete("other");
		if (byCategory.size === 0) {
			const clauses = others.map((item) => partsFor(item, isRunning(item, live)));
			return {
				shown: clauses.slice(0, SUMMARY_CAP),
				more: Math.max(clauses.length - SUMMARY_CAP, 0),
				active
			};
		}
		const categories = [...byCategory.entries()];
		const shown = categories.slice(0, SUMMARY_CAP).map(([category, its]) => categoryClause(category, its, live));
		const hidden = categories.slice(SUMMARY_CAP).reduce((sum, [, its]) => sum + its.length, 0);
		return {
			shown,
			more: others.length + hidden,
			active
		};
	}
	// src/components/chatlog/helpers.ts
	/** Clauses after the first read as one sentence ("Ran 3 commands, read a
	* file"); an acronym-led verb ("PDF ...") keeps its capitals. */
	function inSentence(parts, index) {
		if (index === 0 || !/^[A-Z][a-z]/.test(parts.verb)) return parts;
		return {
			...parts,
			verb: parts.verb[0].toLowerCase() + parts.verb.slice(1)
		};
	}
	exports.inSentence = inSentence;
	exports.isRunning = isRunning;
	exports.summarizeGroupParts = summarizeGroupParts;
	exports.summarizeItemParts = summarizeItemParts;
	return exports;
})({});
