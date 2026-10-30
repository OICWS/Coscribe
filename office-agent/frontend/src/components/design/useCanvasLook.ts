import { useState } from "react";
import { placeOnCanvas, type Canvas } from "../../lib/designCanvas";

export type Scheme = "light" | "dark";

/** How the artboards look on the canvas: light or dark (the server answers each page's
 * `prefers-color-scheme` as asked), and the canvas's variables. A set variable reloads every
 * artboard, since the server puts the variables into each page as it serves it. */
export function useCanvasLook(threadId: string, path: string, setCanvas: (canvas: Canvas) => void, onProblem: (problem: string) => void) {
  const [scheme, setScheme] = useState<Scheme>("light");
  const [variablesOpen, setVariablesOpen] = useState(false);
  const [served, setServed] = useState(0);

  const setVariable = (name: string, value: string) => {
    placeOnCanvas(threadId, path, {}, undefined, { [name]: value })
      .then((canvas) => {
        setCanvas(canvas);
        setServed((n) => n + 1);
      })
      .catch((e: unknown) => onProblem(e instanceof Error ? e.message : String(e)));
  };

  return {
    scheme,
    setScheme,
    variablesOpen,
    setVariablesOpen,
    served,
    setVariable,
  };
}
