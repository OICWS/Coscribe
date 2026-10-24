import { useEffect, useRef, useState } from "react";

const hasFiles = (event: DragEvent) => event.dataTransfer?.types.includes("Files") ?? false;

/** Files dragged over the whole window, not only the message box: `dragging` is true while they are
 * over it, and a drop that nothing else took goes to `onFiles`. Dragging a thread or a slide
 * carries no files, so it is left alone. Without this, a file dropped beside the message box makes
 * the desktop app open the file in place of the page. */
export function useWindowFileDrop(onFiles: (files: File[]) => void, enabled: boolean) {
  const [dragging, setDragging] = useState(false);
  const onFilesRef = useRef(onFiles);
  onFilesRef.current = onFiles;

  useEffect(() => {
    if (!enabled) return;
    // dragenter and dragleave fire once per element the pointer crosses, so a flag would blink.
    let depth = 0;
    const end = () => {
      depth = 0;
      setDragging(false);
    };
    const onEnter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth += 1;
      setDragging(true);
    };
    const onOver = (event: DragEvent) => {
      // A drop only fires on a target that allowed it.
      if (hasFiles(event)) event.preventDefault();
    };
    const onLeave = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const onDrop = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      // A target that handled the drop (a picture dropped into a document, a skill's upload box)
      // has already called preventDefault.
      const taken = event.defaultPrevented;
      event.preventDefault();
      end();
      // A dialog is open over the page: what is dropped on it is not meant for the message box.
      if (taken || document.querySelector('[role="dialog"], [aria-modal="true"]')) return;
      const files = Array.from(event.dataTransfer?.files ?? []);
      if (files.length) onFilesRef.current(files);
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragover", onOver);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("drop", onDrop);
    window.addEventListener("dragend", end);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("drop", onDrop);
      window.removeEventListener("dragend", end);
      setDragging(false);
    };
  }, [enabled]);

  return dragging;
}
