import { type LogItem } from "../../state/reducer";

export type ToolOrApprovalItem = Extract<LogItem, { kind: "tool" | "approval" }>;

export type TaskDraftItem = Extract<LogItem, { kind: "task_draft" }>;
