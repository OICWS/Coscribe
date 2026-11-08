import { capitalize, connectorLabel } from "./runLabels";

const WORD_LABELS: Record<string, string> = {
  pdf: "PDF",
  xlsx: "Excel",
  docx: "Word",
  pptx: "PowerPoint",
  python: "Python",
  node: "Node",
  xml: "XML",
  url: "URL",
  csv: "CSV",
  mcp: "MCP",
};

/** "edit_xlsx_cells" -> "Edit Excel cells". */
export function toolLabel(name: string): string {
  const words = name.split("_").filter(Boolean);
  return capitalize(words.map((w) => WORD_LABELS[w] ?? w).join(" "));
}

/** The connector a connector tool came from: its tools are named "<connector>_<tool>". */
export function connectorOfTool(tool: string): string {
  const server = tool.split("_")[0] ?? "";
  return server && server !== tool ? connectorLabel(server) : "";
}

/** A connector tool without its connector's prefix: "gmail_search_messages" -> "Search messages". */
export function connectorToolLabel(tool: string): string {
  const server = tool.split("_")[0] ?? "";
  return toolLabel(server && server !== tool ? tool.slice(server.length + 1) : tool);
}
