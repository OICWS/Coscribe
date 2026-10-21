import { createContext } from "react";
import type { SteerActions } from "../../lib/steerNotes";

/** The Background tasks panel leaves out the "+N -M" line counts. */
export const ShowDiffStats = createContext(true);

export const NO_CONNECTOR_TOOLS: ReadonlySet<string> = new Set();

export const ConnectorTools = createContext(NO_CONNECTOR_TOOLS);

export const SteerActionsContext = createContext<SteerActions | null>(null);
