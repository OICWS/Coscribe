import { baseName } from "../lib/fileMentions";
import type { LiveDocs } from "../lib/docDrafts";
import { KindIcon } from "./artifacts";
import type { Notice } from "./NoticeStack";

export function docDraftNotices(drafts: LiveDocs, open: (path: string) => boolean): Notice[] {
  return Object.values(drafts).filter((draft) => draft.new && !draft.committed).map((draft) => ({
    id: `doc-draft:${draft.id}`,
    title: baseName(draft.path),
    detail: "Document draft",
    icon: <KindIcon kind="docs" className="h-4 w-4" />,
    onOpen: () => open(draft.path),
    openTitle: `Preview draft ${baseName(draft.path)}`,
    actions: [],
  }));
}
