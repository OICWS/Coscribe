import { useEffect, useState } from "react";

/** The async investigation endpoint returns a thread before its first message exists. */
export function useInvestigationHandoff(threadId: string, hasMessages: boolean) {
  const [pendingThread, setPendingThread] = useState<string | null>(null);
  useEffect(() => {
    if (pendingThread === threadId && hasMessages) setPendingThread(null);
  }, [pendingThread, threadId, hasMessages]);
  return [pendingThread === threadId && !hasMessages, setPendingThread] as const;
}
