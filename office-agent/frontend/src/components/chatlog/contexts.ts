import { openThreadFile } from "../../lib/rest";
import { createContext } from "react";
import type { MessageActions } from "../../lib/messageActions";
import type { SteerActions } from "../../lib/steerNotes";
import type { CardAnswers, CardState } from "../../lib/questionCards";
import type { QuestionSpec } from "../../types/wire";

export const NO_CONNECTOR_TOOLS: ReadonlySet<string> = new Set();

export const ConnectorTools = createContext(NO_CONNECTOR_TOOLS);

/** Opens a deck or document in its panel; false for a file the panels do not show. */
export const ViewFile = createContext<((path: string) => boolean) | null>(null);

/** Opens a design system of the library in Settings; null where it cannot. */
export const OpenDesignSystem = createContext<((id: string) => void) | null>(null);

/** Opens a connector's page in Settings > Connectors; null where it cannot. */
export const OpenConnector = createContext<((name: string) => void) | null>(null);

/** Lets the script a running tool call waits on carry on as a background task; null where it cannot. */
export const DetachScript = createContext<((script: string) => void) | null>(null);

export const SteerActionsContext = createContext<SteerActions | null>(null);

/** Rewind and Edit on a sent message; null where the history can't be cut (before a /compact). */
export const MessageActionsContext = createContext<MessageActions | null>(null);

/** The files this conversation made or changed, by file name: a reply that names one shows a chip. */
export const ThreadFiles = createContext<ReadonlyMap<string, string>>(new Map());
export const FileCheckRevision = createContext(0);

/** The state of this conversation's background tasks by task_id, and how to open one in its panel. */
export const BackgroundTasks = createContext<{ statuses: Readonly<Record<string, string>>; open: (taskId: string) => void }>({
  statuses: {},
  open: () => {},
});

/** A file a reply names or a turn ends with: shown in its panel when the app has one, else opened in
 * the program the computer keeps for it (a Word file in Word). */
export function openMentioned(view: (path: string) => boolean, threadId: string, path: string): void {
  if (!view(path)) void openThreadFile(threadId, path, false);
}

/** Every ask_user_question card's state in this conversation, by its call's id. */
export const QuestionCardStates = createContext<ReadonlyMap<string, CardState>>(new Map());

/** Answering a card: an ask_user_question card's click goes out as the person's message; a
 * remember card's answer goes to the turn waiting on it. null where nothing can be answered. */
export interface QuestionActions {
  answer: (questions: QuestionSpec[], answers: CardAnswers) => void;
  answerPending: (id: string, answers: CardAnswers) => void;
}
export const QuestionActionsContext = createContext<QuestionActions | null>(null);
