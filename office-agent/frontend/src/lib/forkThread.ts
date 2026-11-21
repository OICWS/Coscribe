import { goToThread } from "./nav";
import { forkThread } from "./rest";

/** /fork [name] and a reply's Fork button: the copy opens as soon as it exists, and the original
 * stays as it was in the sidebar. */
export function forkAndOpen(
  threadId: string,
  title: string,
  name: string,
  upto: number | undefined,
  onOpened: () => void,
  onError: (message: string) => void,
): void {
  void forkThread(threadId, name.trim() || `${title} (fork)`, upto).then((result) => {
    if ("error" in result) return onError(result.error);
    goToThread(result.thread_id);
    onOpened();
  });
}
