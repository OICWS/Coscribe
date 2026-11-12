import { useEffect, useRef, useState, type ReactNode } from "react";
import { KINDS } from "../lib/artifacts";
import { copyImage } from "../lib/copyImage";
import { getDoc } from "../lib/docFile";
import { KIND_WORDS } from "../lib/fileMentions";
import { changedWhen, closeKey, folderOf, isImageFile, madeOutputs, titleOf, type MadeOutput } from "../lib/madeOutputs";
import { getThreadActivity, openThreadFile, threadFileDownloadUrl } from "../lib/rest";
import { readStored, writeStored } from "../lib/storage";
import { isDocMarkdown } from "../lib/viewers";
import type { ActivityFile } from "../types/session";
import { KindIcon } from "./artifacts/artifactIcons";
import { FolderIcon } from "./icons";
import { ImageGallery } from "./ImageGallery";
import { FileIcon, FileSheetIcon } from "./files/fileIcons";
import type { Notice } from "./NoticeStack";

const CLOSED_KEY = "coscribe.closedOutputNotices";
const REFRESH_DEBOUNCE_MS = 400;

const EXTERNAL_COLOURS: Record<string, string> = {
  Excel: "var(--file-sheet)",
  CSV: "var(--file-sheet)",
  PDF: "var(--file-pdf)",
  Word: "var(--file-doc)",
  PowerPoint: "var(--file-slides)",
};

const imageSrc = (threadId: string, file: ActivityFile) =>
  `${threadFileDownloadUrl(threadId, file.path)}&v=${encodeURIComponent(file.modified_at ?? "")}`;

function useClosed() {
  const [closed, setClosed] = useState<Set<string>>(() => {
    try {
      return new Set(JSON.parse(readStored(CLOSED_KEY) ?? "[]") as string[]);
    } catch {
      return new Set();
    }
  });
  const close = (keys: string[]) =>
    setClosed((prev) => {
      const next = new Set([...prev, ...keys]);
      writeStored(CLOSED_KEY, JSON.stringify([...next].slice(-200)));
      return next;
    });
  return [closed, close] as const;
}

/** The Markdown files among the outputs that the server reads as Docs: a notes file the model
 * wrote is not a document to offer. */
function useDocs(threadId: string, outputs: ActivityFile[]): Set<string> {
  const [docs, setDocs] = useState<Set<string>>(new Set());
  const asked = useRef(new Set<string>());
  useEffect(() => {
    for (const file of outputs) {
      const key = `${threadId}\u0000${file.path}\u0000${file.modified_at ?? ""}`;
      if (!isDocMarkdown(file.path) || asked.current.has(key)) continue;
      asked.current.add(key);
      getDoc(threadId, file.path).then(
        () => setDocs((prev) => new Set(prev).add(`${threadId}\u0000${file.path}`)),
        () => undefined,
      );
    }
  }, [threadId, outputs]);
  return new Set([...docs].filter((key) => key.startsWith(`${threadId}\u0000`)).map((key) => key.slice(threadId.length + 1)));
}

const NONE: ActivityFile[] = [];

/** What the conversation made, fetched again a moment after each finished call, with when it was
 * fetched to say how long ago each file changed. */
function useOutputs(threadId: string, refreshKey: string): { outputs: ActivityFile[]; at: Date } {
  const [fetched, setFetched] = useState({ threadId: "", outputs: NONE, at: new Date(0) });
  const request = useRef(0);
  useEffect(() => {
    const mine = ++request.current;
    const timer = window.setTimeout(() => {
      getThreadActivity(threadId).then(
        (activity) => mine === request.current && setFetched({ threadId, outputs: activity.outputs, at: new Date() }),
        () => undefined,
      );
    }, REFRESH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [threadId, refreshKey]);
  return fetched.threadId === threadId ? fetched : { outputs: NONE, at: fetched.at };
}

interface OutputActions {
  /** Shows a file in its panel; false when the app can't show it. */
  view: (path: string) => boolean;
}

/** The documents, decks, designs, pictures and files the conversation made, each a notice above
 * the message box until the person closes it; a file changed again comes back. Gives the picture
 * viewer to render beside the notices too. */
export function useOutputNotices(
  threadId: string,
  refreshKey: string,
  on: OutputActions,
): { notices: Notice[]; overlay: ReactNode } {
  const { outputs, at: now } = useOutputs(threadId, refreshKey);
  const docs = useDocs(threadId, outputs);
  const [closed, close] = useClosed();
  const [gallery, setGallery] = useState<{ files: ActivityFile[]; index: number } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const open = (file: ActivityFile) => {
    if (!on.view(file.path)) void openThreadFile(threadId, file.path, false);
  };
  const copy = (file: ActivityFile) => {
    copyImage(imageSrc(threadId, file)).then(
      () => {
        setCopied(file.path);
        window.setTimeout(() => setCopied((path) => (path === file.path ? null : path)), 1500);
      },
      () => undefined,
    );
  };

  const notices: Notice[] = [];
  const made = madeOutputs(outputs, docs)
    .map((output): MadeOutput | null => {
      if (output.kind !== "images") return closed.has(closeKey(threadId, output.file)) ? null : output;
      const files = output.files.filter((file) => !closed.has(closeKey(threadId, file)));
      return files.length ? { kind: "images", files } : null;
    })
    .filter((output): output is MadeOutput => output !== null);

  for (const output of made.reverse()) {
    if (output.kind === "artifact") {
      const { file, artifact } = output;
      const when = changedWhen(file.modified_at, now);
      notices.push({
        id: `made:${file.path}`,
        icon: <KindIcon kind={artifact} className="h-4 w-4" style={{ color: KINDS[artifact].colour }} />,
        title: titleOf(file.name),
        plainTitle: true,
        detail: [KIND_WORDS[artifact], file.action === "created" ? `new${when ? ` · ${when}` : ""}` : `updated ${when}`.trim()].join(" · "),
        onOpen: () => open(file),
        openTitle: `Open ${file.name}`,
        actions: [],
        onDismiss: () => close([closeKey(threadId, file)]),
      });
    } else if (output.kind === "images") {
      const { files } = output;
      const first = files[0];
      const folder = folderOf(first.path);
      const one = files.length === 1;
      notices.push({
        id: "made:images",
        icon: null,
        thumbnails: files.map((file) => imageSrc(threadId, file)),
        title: one ? first.name : `${files.length} pictures`,
        plainTitle: true,
        detail: [folder ? `in ${folder}` : "", changedWhen(first.modified_at, now)].filter(Boolean).join(" · "),
        onOpen: () => setGallery({ files, index: 0 }),
        openTitle: one ? `View ${first.name}` : "View the pictures",
        actions: one
          ? [{ label: copied === first.path ? "Copied" : "Copy", title: "Copy the picture", onClick: () => copy(first) }]
          : [{ label: "View all", onClick: () => setGallery({ files, index: 0 }) }],
        onDismiss: () => close(files.map((file) => closeKey(threadId, file))),
      });
    } else {
      const { file, type } = output;
      const folder = folderOf(file.path);
      notices.push({
        id: `made:${file.path}`,
        icon: type === "Excel" || type === "CSV"
          ? <FileSheetIcon className="h-4 w-4" style={{ color: EXTERNAL_COLOURS[type] }} />
          : <FileIcon className="h-4 w-4" style={{ color: EXTERNAL_COLOURS[type] }} />,
        title: file.name,
        detail: [type, folder].filter(Boolean).join(" · "),
        plainDetail: true,
        actions: [
          { label: "Open", title: `Open in its own program`, onClick: () => void openThreadFile(threadId, file.path, false) },
          { label: "Show in folder", icon: <FolderIcon className="h-4 w-4" />, onClick: () => void openThreadFile(threadId, file.path, true) },
        ],
        onDismiss: () => close([closeKey(threadId, file)]),
      });
    }
  }

  const overlay = gallery && (
    <ImageGallery
      images={gallery.files.filter((file) => isImageFile(file.path)).map((file) => ({ name: file.name, src: imageSrc(threadId, file) }))}
      start={gallery.index}
      onClose={() => setGallery(null)}
    />
  );
  return { notices, overlay };
}
