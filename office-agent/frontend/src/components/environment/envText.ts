/** The environment variables page edits `.env` text: one KEY=value per line, `#` comments, and
 * quoted values that may span lines. */

export type EnvParse = { variables: Record<string, string> } | { error: string };

const NAME = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
const MAX_VARIABLES = 100;
const MAX_VARIABLE_VALUE = 4096;

/** Where a quoted value starting at `start` (just after the opening quote) ends, or -1. */
function closingQuote(text: string, start: number, quote: string): number {
  for (let i = start; i < text.length; i++) {
    if (quote === '"' && text[i] === "\\") i++;
    else if (text[i] === quote) return i;
  }
  return -1;
}

function unescapeDouble(raw: string): string {
  return raw.replace(/\\([\\"n])/g, (_, c: string) => (c === "n" ? "\n" : c));
}

export function parseEnvText(text: string): EnvParse {
  const variables: Record<string, string> = {};
  const source = text.replace(/\r\n?/g, "\n");
  let pos = 0;
  let lineNo = 0;
  while (pos <= source.length) {
    const newline = source.indexOf("\n", pos);
    const end = newline === -1 ? source.length : newline;
    const lineStart = pos;
    const line = source.slice(pos, end);
    lineNo++;
    pos = end + 1;
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const match = /^(?:export\s+)?([^=\s]+)\s*=\s*(.*)$/.exec(trimmed);
    if (!match) return { error: `Line ${lineNo}: expected KEY=value.` };
    const key = match[1];
    if (!NAME.test(key)) {
      return { error: `Line ${lineNo}: "${key}" isn't a variable name (letters, digits and underscores).` };
    }
    if (key in variables) return { error: `Line ${lineNo}: ${key} appears twice.` };

    const rest = match[2];
    let value: string;
    const quote = rest[0];
    if (quote === '"' || quote === "'") {
      // The value starts after the quote in the original text, so a quoted value can run over lines.
      const valueStart = lineStart + line.indexOf(trimmed) + trimmed.length - rest.length + 1;
      const close = closingQuote(source, valueStart, quote);
      if (close === -1) return { error: `Line ${lineNo}: the quote is never closed.` };
      const raw = source.slice(valueStart, close);
      value = quote === '"' ? unescapeDouble(raw) : raw;
      const afterEnd = source.indexOf("\n", close);
      const tail = source.slice(close + 1, afterEnd === -1 ? source.length : afterEnd).trim();
      if (tail && !tail.startsWith("#")) return { error: `Line ${lineNo}: unexpected text after the closing quote.` };
      lineNo += raw.split("\n").length - 1;
      pos = afterEnd === -1 ? source.length + 1 : afterEnd + 1;
    } else {
      value = rest.replace(/\s+#.*$/, "").trim();
    }
    if (value.length > MAX_VARIABLE_VALUE) {
      return { error: `The value of ${key} is longer than ${MAX_VARIABLE_VALUE} characters.` };
    }
    variables[key] = value;
    if (Object.keys(variables).length > MAX_VARIABLES) return { error: `At most ${MAX_VARIABLES} variables.` };
  }
  return { variables };
}

function formatValue(value: string): string {
  if (value === "" || !/[\s"'#\\]/.test(value)) return value;
  return `"${value.replace(/[\\"]/g, "\\$&")}"`;
}

export function formatEnvText(variables: Record<string, string>): string {
  return Object.entries(variables)
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join("\n");
}
