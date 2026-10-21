import { createContext } from "react";
import type { SteerActions } from "../../lib/steerNotes";

/** The Background tasks panel leaves out the "+N -M" line counts. */
export const ShowDiffStats = createContext(true);

export const NO_CONNECTOR_TOOLS: ReadonlySet<string> = new Set();

export const ConnectorTools = createContext(NO_CONNECTOR_TOOLS);

/** Opens a deck or document in its panel; false for a file the panels do not show. */
export const ViewFile = createContext<((path: string) => boolean) | null>(null);

export const SteerActionsContext = createContext<SteerActions | null>(null);
