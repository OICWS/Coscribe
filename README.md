# Coscribe

[![CI](https://github.com/OICWS/coscribe/actions/workflows/office-agent-ci.yml/badge.svg)](https://github.com/OICWS/coscribe/actions/workflows/office-agent-ci.yml)

A local, user-friendly assistant for office work. It reads and writes your
files, produces Word, Excel, PowerPoint and PDF documents, makes Docs, slide
decks, designs and dashboards you edit beside the conversation, uses the web
in a browser of its own and your tools, and can repeat work on a schedule. It
runs on your computer and needs only a model API key.

Website: https://oicws.github.io/Coscribe/

## Use the desktop app (Windows)

1. Download the portable build from
   [GitHub Releases](https://github.com/OICWS/coscribe/releases) (currently the
   `beta` pre-release), unzip it anywhere and start `Coscribe.exe`. Nothing is
   installed. The build is not code-signed yet, so Windows SmartScreen warns on
   the first start: choose **More info → Run anyway**.
2. Open **Settings › Providers**, pick a model service and paste its API key
   (or add any OpenAI-compatible service yourself).
3. Pick a **workspace**, the folder you work in, under the message box, and ask.

The desktop app adds what a browser tab can't: the built-in browser panel, the
taskbar flashing when a conversation needs you, and keeping the computer awake
while a task runs.
To build it yourself, see [`office-agent-desktop/`](office-agent-desktop/).

## What makes it different

- **Office documents done properly.** Real `.docx`, `.xlsx` and `.pptx` files with
  native charts, formulas computed and written in, tracked changes and comments.
  Every file is rendered and the pages are checked, so the model sees what it made
  rather than guessing. Microsoft Office or WPS on your machine draws the previews;
  LibreOffice is optional.
- **Artifacts beside the chat.** Docs, slide decks, designs (a canvas of boards you
  present or export as PNG) and data dashboards open in a panel next to the
  conversation, where you edit them, and are all listed on the Artifacts page.
- **A browser the AI uses in front of you.** In the desktop app Coscribe has its own
  browser with your sign-ins kept. The AI fills whole forms, uploads and downloads
  files, saves tables across pages as CSV and pages as PDF, and hands a sign-in or a
  captcha back to you. You can take over at any moment, point at an element, or mark
  up a screenshot and send it. Each site has a level in the workspace: used without
  asking, asked about first, or kept out.
- **Work that repeats becomes a task.** A conversation that worked can be saved as a
  workflow of fixed steps that runs on a schedule, when a file arrives in a folder,
  when something new shows up in a connector, or when another program sends an event.
  You choose how much the AI may decide on its own, from fixed steps to self-healing
  (a failed browser step is redone on the page as it is now) to fully autonomous. A
  task can also watch a page and tell you when a price or status changes. Every run
  ends with a report.
- **You stay in control.** Four permission modes (Manual, Accept Edits, Plan, and Auto,
  where a reviewer model approves on your behalf). Plans can be reviewed and edited
  before work starts, and any sent message can be rewound or edited. On Windows,
  scripts run in an isolated sandbox that reaches only the folders you allowed.
  Every decision goes to an audit log.
- **Checks its own work.** A separate reviewer with read-only tools checks finished
  documents against what the scripts actually returned, so a figure nothing produced
  stands out. Larger jobs are split across sub-agents.
- **Your models.** Anthropic, OpenAI and Gemini directly, and any OpenAI-compatible
  API, with presets for DeepSeek, Kimi, GLM, Qwen, Doubao, OpenRouter, Mistral, Groq,
  local runners (Ollama, LM Studio) and more. Prompt caching is tuned per provider,
  and the tokens each turn used are shown.
- **Connectors, skills and memory.** Hosted services you sign in to once in your own
  browser (no app to register), skills (folders of instructions and files) you can
  read before adding, and global instructions plus notes a workspace folder keeps for
  itself.
- **Code when you need it.** Programming tasks can be handed to Codex, an optional
  module downloaded on first use.

## Run it from source

The same app also runs as a web UI in your own browser, without the built-in
browser panel (Coscribe is developed and verified on Windows):

```bash
cd office-agent
python3 -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install uv && python scripts/install_locked.py --extra dev --extra web   # the versions in uv.lock
cp .env.example .env                                   # add a model API key
(cd frontend && npm install && npm run build)
coscribe-web                                           # the web UI on http://127.0.0.1:8000
```

[`office-agent/README.md`](office-agent/README.md) has the full setup and every
feature in detail.

## Repository

| Path | |
|---|---|
| `office-agent/` | The Python backend, the React frontend and the tests |
| `office-agent-desktop/` | The Electron desktop shell |
| `docs/` | Engineering docs: the plan, decisions, the log of what shipped |
| `site/` | The project website (GitHub Pages) |

## Contributing

Developers and AI coding sessions: start with [`CLAUDE.md`](CLAUDE.md) (a map
of the code and what to read first) and [`CONTRIBUTING.md`](CONTRIBUTING.md).
Before every change run `cd office-agent && bash scripts/check.sh`.

Security issues: see [`SECURITY.md`](SECURITY.md). Behaviour in the project:
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
