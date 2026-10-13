import { createContext } from "react";

/** The Background tasks panel leaves out the "+N -M" line counts. */
export const ShowDiffStats = createContext(true);

export const NO_CONNECTOR_TOOLS: ReadonlySet<string> = new Set();

export const ConnectorTools = createContext(NO_CONNECTOR_TOOLS);
