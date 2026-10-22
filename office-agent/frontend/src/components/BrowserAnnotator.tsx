import { ImageAnnotator } from "./ImageAnnotator";
import type { BrowserCapture } from "./PickedPreview";

export interface PageCapture {
  dataUrl: string;
  title: string;
  url: string;
}

/** A still screenshot of the current page to draw on and send to the chat, for pointing at something
 * faster than describing it. */
export function BrowserAnnotator({
  capture,
  onClose,
  onSendToChat,
}: {
  capture: PageCapture;
  onClose: () => void;
  onSendToChat: (capture: BrowserCapture) => void;
}) {
  return (
    <ImageAnnotator
      fill
      src={capture.dataUrl}
      saveLabel="Add to chat"
      onClose={onClose}
      onSave={(dataUrl, notes) => {
        let text = `Annotated screenshot of the browser page "${capture.title}" (${capture.url}) -- the drawn marks point at what the user means`;
        if (notes.length) text += `; notes written on it: ${notes.join(", ")}`;
        onSendToChat({ name: "annotation.jpg", dataUrl, text, source: "annotation" });
        onClose();
      }}
    />
  );
}
