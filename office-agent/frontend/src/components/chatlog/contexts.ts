import { createContext } from "react";
import type { SteerActions } from "../../lib/steerNotes";

/** The Background tasks panel leaves out the "+N -M" line counts. */
export const ShowDiffStats = createContext(true);

export const NO_CONNECTOR_TOOLS: ReadonlySet<string> = new Set();

export const ConnectorTools = createContext(NO_CONNECTOR_TOOLS);

/** Opens a deck or document in its panel; false for a file the panels do not show. */
export const ViewFile = createContext<((path: string) => boolean) | null>(null);

/** Opens a design system of the library in Settings; null where it cannot. */
export const OpenDesignSystem = createContext<((id: string) => void) | null>(null);

/** Lets the script a running tool call waits on carry on as a background task; null where it cannot. */
export const DetachScript = createContext<((script: string) => void) | null>(null);

export const SteerActionsContext = createContext<SteerActions | null>(null);

/** The files this conversation made or changed, by file name: a reply that names one shows a chip. */
export const ThreadFiles = createContext<ReadonlyMap<string, string>>(new Map());

/** The state of this conversation's background tasks by task_id, and how to open one in its panel. */
export const BackgroundTasks = createContext<{ statuses: Readonly<Record<string, string>>; open: (taskId: string) => void }>({
  statuses: {},
  open: () => {},
});
