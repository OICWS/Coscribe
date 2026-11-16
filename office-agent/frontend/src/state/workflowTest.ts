import type { DraftTestProgress } from "../types/workflow";
import type { WsServerEvent } from "../types/wire";

export function testProgress(previous: DraftTestProgress | null, action: Extract<WsServerEvent, { type: "workflow_test_progress" }>): DraftTestProgress {
  const records = previous?.toolCallId === action.tool_call_id ? previous.records ?? [] : [];
  const record = action.record;
  return {
    done: action.done, total: action.total, toolCallId: action.tool_call_id,
    records: record ? [...records.filter(r => r.step_id !== record.step_id || JSON.stringify(r.iteration) !== JSON.stringify(record.iteration)), record] : records,
  };
}

