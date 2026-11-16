import { AsyncLocalStorage } from "node:async_hooks";

/** A step under way, and whether its conversation was stopped. Conversations
 * run steps side by side, so each step finds its own through its async context. */
export interface Step {
  threadId: string;
  requestId: string;
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
  const next = (queues.get(threadId) ?? Promise.resolve()).catch(() => undefined).then(work);
  queues.set(threadId, next);
  void next.catch((error) => console.error("Browser step failed:", error)).finally(() => {
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

/** A renderer can stop answering without emitting a navigation or dialog event.
 * Bound each protocol operation so it cannot hold the conversation's queue forever. */
export async function browserOperation<T>(work: Promise<T>, timeoutMs = 20_000): Promise<T> {
  const step = stepContext.getStore();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let poll: ReturnType<typeof setInterval> | undefined;
  try {
    return await Promise.race([work, new Promise<never>((_resolve, reject) => {
      const check = () => { if (step?.stop) reject(new Error("Stopped by the user or a timed-out browser request.")); };
      check();
      poll = setInterval(check, 50);
      timer = setTimeout(() => reject(new Error("The browser stopped responding; list the tabs and retry the step.")), timeoutMs);
    })]);
  } finally {
    clearTimeout(timer);
    clearInterval(poll);
  }
}

/** Control messages bypass the queue so a waiting step can actually be cancelled. */
export function handleBrowserControl(
  command: { action: string; thread_id: string; args: Record<string, unknown> },
  stoppedAt: Map<string, number>,
  cancelledRequests: Set<string>,
  activity: (thread: string, active: boolean) => void,
): boolean {
  const step = runningSteps.get(command.thread_id);
  if (command.action === "activity") activity(command.thread_id, Boolean(command.args.active));
  else if (command.action === "cancel_request") {
    const id = String(command.args.request_id);
    if (step?.requestId === id) step.stop = true;
    else {
      cancelledRequests.add(id);
      // Late cancellation replies must not accumulate for the life of the app.
      if (cancelledRequests.size > 1000) cancelledRequests.delete(cancelledRequests.values().next().value!);
    }
  } else if (command.action === "cancel") {
    stoppedAt.set(command.thread_id, Date.now());
    if (step) step.stop = true;
  } else return false;
  return true;
}
