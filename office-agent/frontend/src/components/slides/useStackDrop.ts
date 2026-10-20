import { useState } from "react";
import { STACK, elementsOf, inStack, type Box } from "../../lib/slideSource";
import { dropTarget, moveInto, moveOut, stackSlots, type Drop } from "../../lib/slideStacks";

type Change = (edit: (elements: Element[]) => void, redraw: boolean) => void;

/** Dragging an element over a slide with containers: where it would land (shown while the pointer
 * moves), and on the drop, the element moved into that container, within it, or out of it onto the
 * slide. The server lays the section out again after the change. */
export function useStackDrop(doc: Document | null, boxes: (Box | null)[], change: Change, select: (at: number) => void) {
  const [drop, setDrop] = useState<Drop | null>(null);

  const track = (index: number, x: number, y: number) => {
    if (!doc || !elementsOf(doc).some((el) => el.localName === STACK)) return;
    setDrop(dropTarget(stackSlots(doc, boxes, elementsOf(doc)[index]), x, y));
  };

  /** The drag ended with the element's box at `box`: true when it was a move into, within or out
   * of a container, which is made here; false leaves a plain move to the caller. */
  const finish = (index: number, box: Box): boolean => {
    const target = drop;
    setDrop(null);
    if (!doc) return false;
    const el = elementsOf(doc)[index];
    if (!target && !inStack(el)) return false;
    change((els) => {
      if (target) moveInto(els[index], els[target.node], target.at);
      else moveOut(els[index], box.map(Math.round) as Box);
    }, true);
    select(elementsOf(doc).indexOf(el));
    return true;
  };

  return { drop, track, finish, clear: () => setDrop(null) };
}
