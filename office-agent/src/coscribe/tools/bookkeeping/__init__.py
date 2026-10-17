"""The model's own bookkeeping: its task list, scheduled tasks, sub-agent and background runs,
self-wakes, messages between conversations, questions and plan choices, and the memory file."""

from __future__ import annotations

from .background_tasks import BackgroundTask, BackgroundTaskStore, build_background_task_tools
from .conversations import MessagingStore, build_conversation_tools, format_incoming
from .interaction import (
    PLAN_CHOICE_AUTO,
    PLAN_CHOICE_MANUAL,
    PLAN_CHOICE_REVISE,
    QUESTION_TOOL_NAMES,
    build_interaction_tools,
    format_question_answers,
    normalize_questions,
)
from .memory import format_memory_section, load_memory
from .scheduled_tasks import (
    SCHEDULED_THREAD_PREFIX,
    TASK_DRAFT_TOOL_NAMES,
    ScheduledRun,
    ScheduledTrigger,
    ScheduledTriggerStore,
    ScheduleRule,
    build_scheduled_task_tools,
    compute_next_run_at,
    create_trigger,
    edit_draft,
    parse_run_thread_id,
    patch_trigger,
    record_draft,
    update_trigger,
)
from .selfwake import (
    SignalStore,
    WakeRequest,
    WakeStore,
    build_selfwake_tools,
)
from .subagent_tasks import (
    SubAgentTask,
    SubAgentTaskStore,
    build_subagent_task_tools,
    forget_finished_subagents,
    get_subagent_transcript,
    running_subagent,
    stop_subagent_task,
)
from .tasks import build_task_tools

__all__ = [
    "PLAN_CHOICE_AUTO",
    "PLAN_CHOICE_MANUAL",
    "PLAN_CHOICE_REVISE",
    "QUESTION_TOOL_NAMES",
    "SCHEDULED_THREAD_PREFIX",
    "TASK_DRAFT_TOOL_NAMES",
    "BackgroundTask",
    "BackgroundTaskStore",
    "MessagingStore",
    "ScheduleRule",
    "ScheduledRun",
    "ScheduledTrigger",
    "ScheduledTriggerStore",
    "SignalStore",
    "SubAgentTask",
    "SubAgentTaskStore",
    "WakeRequest",
    "WakeStore",
    "build_background_task_tools",
    "build_conversation_tools",
    "build_interaction_tools",
    "build_scheduled_task_tools",
    "build_selfwake_tools",
    "build_subagent_task_tools",
    "build_task_tools",
    "compute_next_run_at",
    "create_trigger",
    "edit_draft",
    "forget_finished_subagents",
    "format_incoming",
    "format_memory_section",
    "format_question_answers",
    "get_subagent_transcript",
    "load_memory",
    "normalize_questions",
    "parse_run_thread_id",
    "patch_trigger",
    "record_draft",
    "running_subagent",
    "stop_subagent_task",
    "update_trigger",
]
