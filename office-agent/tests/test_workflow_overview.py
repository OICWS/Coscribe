"""What the model is shown to write a task's one-sentence overview, and how its reply is cleaned."""

from coscribe.workflow_spec import parse_workflow
from coscribe.workflows.overview import OVERVIEW_CHARS, clean_overview, overview_request


def test_the_request_names_steps_by_title_with_what_they_work_out() -> None:
    workflow = parse_workflow(
        {
            "inputs": [{"name": "day", "label": "Day", "type": "date"}],
            "steps": [
                {
                    "id": "both",
                    "kind": "parallel",
                    "title": "Gather",
                    "lanes": [
                        {
                            "label": "Agenda",
                            "steps": [
                                {
                                    "id": "a",
                                    "kind": "tool",
                                    "title": "Read the agenda",
                                    "tool": "read_file",
                                    "args": {"path": "a.ics"},
                                }
                            ],
                        },
                        {
                            "label": "Mail",
                            "steps": [
                                {
                                    "id": "m",
                                    "kind": "tool",
                                    "title": "Read the mail",
                                    "tool": "read_file",
                                    "args": {"path": "m.txt"},
                                }
                            ],
                        },
                    ],
                },
                {
                    "id": "sum",
                    "kind": "llm",
                    "title": "Write the briefing",
                    "prompt": "Summarize the day",
                    "fields": [
                        {"name": "headline", "type": "text", "description": "one line for today"}
                    ],
                    "save_as": "brief",
                },
            ],
        }
    )
    request = overview_request("Morning briefing", workflow)
    assert request.startswith("Task: Morning briefing\nAsks for: Day\nSteps:\n")
    assert (
        "- parallel: Gather\n  at the same time, Agenda:\n    - tool: Read the agenda (read_file)"
        in request
    )
    assert "- llm: Write the briefing (works out headline: one line for today)" in request


def test_a_reply_becomes_one_short_line() -> None:
    assert clean_overview('  "Overview: Gathers\nyour  day."  ') == "Gathers your day."
    long = clean_overview("word " * 100)
    assert len(long) <= OVERVIEW_CHARS and long.endswith("…")
