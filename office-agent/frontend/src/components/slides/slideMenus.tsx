import { ZOOM_STEPS, stepZoom, zoomLabel, type SlideExport } from "../../lib/slides";
import { BookOpenIcon, ExternalLinkIcon, FolderIcon, PlayIcon } from "../icons";
import type { MenuEntry } from "./SlideMenu";
import type { SlidesView } from "./SlideStrip";
import type { useSlideHistory } from "./useSlideHistory";

/** The entries of the Slides panel's menus: zoom, download, present, and the presentation's own. */

export function zoomEntries(
  zoom: number,
  view: SlidesView,
  setZoom: (zoom: number | null) => void,
  history: ReturnType<typeof useSlideHistory>,
): MenuEntry[] {
  const now = (step: number) => Math.abs(step - zoom) < 1e-6;
  return [
    {
      label: "Zoom in",
      hint: "Ctrl +",
      disabled: stepZoom(zoom, 1) === zoom,
      onSelect: () => setZoom(stepZoom(zoom, 1)),
    },
    {
      label: "Zoom out",
      hint: "Ctrl −",
      disabled: stepZoom(zoom, -1) === zoom,
      onSelect: () => setZoom(stepZoom(zoom, -1)),
    },
    {
      label: view === "slide" ? "Fit the slide" : "Fit the slides",
      onSelect: () => setZoom(null),
    },
    "divider",
    { note: `Now ${zoomLabel(zoom)}` },
    ...ZOOM_STEPS.map((step) => ({
      label: zoomLabel(step),
      checked: now(step),
      disabled: now(step),
      onSelect: () => setZoom(step),
    })),
    "divider",
    {
      label: history.history.undo === "coscribe" ? "Undo coscribe's change" : "Undo",
      hint: "Ctrl+Z",
      disabled: !history.history.undo,
      onSelect: () => history.step("undo"),
    },
    {
      label: history.history.redo === "coscribe" ? "Redo coscribe's change" : "Redo",
      hint: "Ctrl+Shift+Z",
      disabled: !history.history.redo,
      onSelect: () => history.step("redo"),
    },
  ];
}

export function downloadEntries(download: (format: SlideExport) => void): MenuEntry[] {
  return [
    { label: "PDF (.pdf)", onSelect: () => download("pdf") },
    { label: "Web page (.html)", onSelect: () => download("html") },
    { label: "Current slide as an image (.png)", onSelect: () => download("png") },
    "divider",
    { label: "PowerPoint, current fonts (.pptx)", onSelect: () => download("pptx") },
    { label: "PowerPoint, basic fonts (.pptx)", onSelect: () => download("pptx-basic") },
    { note: "Basic fonts work on any computer" },
  ];
}

export function presentEntries(present: (withNotes: boolean) => void): MenuEntry[] {
  return [
    { label: "Present", icon: <PlayIcon className="h-4 w-4" />, onSelect: () => present(false) },
    { label: "Present with speaker notes", icon: <BookOpenIcon className="h-4 w-4" />, onSelect: () => present(true) },
  ];
}

export function titleEntries(open: (reveal: boolean) => void, history: ReturnType<typeof useSlideHistory>): MenuEntry[] {
  return [
    {
      label: "Open in PowerPoint",
      icon: <ExternalLinkIcon className="h-4 w-4" />,
      onSelect: () => open(false),
    },
    {
      label: "Show in folder",
      icon: <FolderIcon className="h-4 w-4" />,
      onSelect: () => open(true),
    },
    "divider",
    {
      label: "Discard my edits",
      disabled: history.history.undo !== "you",
      onSelect: () => {
        if (window.confirm("Take back every change you made since coscribe's last version of this presentation?")) history.step("discard");
      },
    },
  ];
}

