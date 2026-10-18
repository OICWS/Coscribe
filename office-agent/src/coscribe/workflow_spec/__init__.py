"""What a workflow is: the validated definition of a fixed list of steps and the references
between them. Pure data and string handling, so the schedule store (`tools`) can validate one
and `workflows` can run it without either importing the other."""

from .refs import evaluate, render_text, render_value, resolve
from .spec import (
    ApprovalStep,
    BranchStep,
    CheckStep,
    LLMStep,
    LoopStep,
    OutputField,
    Placed,
    ScriptStep,
    Step,
    ToolStep,
    Workflow,
    parse_workflow,
    step_output,
    walk,
    workflow_error,
)

__all__ = [
    "ApprovalStep",
    "BranchStep",
    "CheckStep",
    "LLMStep",
    "LoopStep",
    "OutputField",
    "Placed",
    "ScriptStep",
    "Step",
    "ToolStep",
    "Workflow",
    "evaluate",
    "parse_workflow",
    "render_text",
    "render_value",
    "resolve",
    "step_output",
    "walk",
    "workflow_error",
]
