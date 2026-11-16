import type { Notice } from "./NoticeStack";
import { WorkflowIcon } from "./icons";

/** After a turn that did a job someone would do again: save it, so it can run again or on a
 * schedule. Each choice gets the job's name; the notice goes away once one is picked. */
export function saveOfferNotice(
  offer: { steps: number; name: string },
  on: { workflow: (name: string) => void; skill: (name: string) => void; dismiss: () => void },
): Notice {
  const pick = (save: (name: string) => void) => () => {
    on.dismiss();
    save(offer.name);
  };
  return {
    id: "save-offer",
    icon: <WorkflowIcon className="h-4 w-4" />,
    title: "Save this job?",
    detail: `${offer.steps} steps, to run again or on a schedule`,
    actions: [
      { label: "Save as skill", onClick: pick(on.skill), title: "Instructions the assistant follows next time" },
      { label: "Save as workflow", onClick: pick(on.workflow), title: "Fixed steps you can rerun or schedule" },
    ],
    onDismiss: on.dismiss,
    dismissTitle: "Not now",
  };
}
