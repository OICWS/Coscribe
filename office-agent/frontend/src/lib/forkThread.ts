import { goToThread } from "./nav";
import { forkThread } from "./rest";

/** /fork [name]: the copy opens as soon as it exists, and the original stays as it was in the
 * sidebar. */
export function forkAndOpen(
  threadId: string,
  title: string,
  name: string,
  onOpened: () => void,
  onError: (message: string) => void,
): void {
  void forkThread(threadId, name.trim() || `${title} (fork)`).then((result) => {
    if ("error" in result) return onError(result.error);
    goToThread(result.thread_id);
    onOpened();
  });
}
