import { AsyncLocalStorage } from "node:async_hooks";

/** A step under way, and whether its conversation was stopped. Conversations
 * run steps side by side, so each step finds its own through its async context. */
export interface Step {
  threadId: string;
  stop: boolean;
}
export const stepContext = new AsyncLocalStorage<Step>();
export const runningSteps = new Map<string, Step>();
export const running = {
  get stop(): boolean {
    return stepContext.getStore()?.stop ?? false;
  },
};

const queues = new Map<string, Promise<void>>();

/** Runs `work` after the thread's earlier work: one step at a time per
 * conversation, while conversations don't wait for each other. */
export function enqueue(threadId: string, work: () => Promise<void>): void {
  const next = (queues.get(threadId) ?? Promise.resolve()).then(work);
  queues.set(threadId, next);
  void next.finally(() => {
    if (queues.get(threadId) === next) queues.delete(threadId);
  });
}

const frameOffTimers = new Map<string, ReturnType<typeof setTimeout>>();

/** Runs `off` in `delayMs` unless the thread takes another step first. */
export function scheduleFrameOff(threadId: string, delayMs: number, off: () => void): void {
  cancelFrameOff(threadId);
  frameOffTimers.set(threadId, setTimeout(off, delayMs));
}

export function cancelFrameOff(threadId: string): void {
  clearTimeout(frameOffTimers.get(threadId));
}
