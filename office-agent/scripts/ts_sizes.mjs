// Usage: node ts_sizes.mjs <root> <dir>...
// Prints {files: {path: lines}, functions: {"path::name": lines}} for the TypeScript under each
// <dir>, with paths relative to <root>. Called by ratchet.py; it parses with the frontend's own
// `typescript` so the numbers need no extra dependency.
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const ts = createRequire(path.join(here, "..", "frontend", "package.json"))("typescript");
const [rootArg, ...dirs] = process.argv.slice(2);
const root = path.resolve(rootArg);

function* sources(dir) {
  for (const entry of readdirSync(dir).sort()) {
    if (entry === "node_modules" || entry === "dist") continue;
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) yield* sources(full);
    else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith(".d.ts")) yield full;
  }
}

function nameOf(node) {
  if (node.name && ts.isIdentifier(node.name)) return node.name.text;
  const parent = node.parent;
  if (parent && ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) return parent.name.text;
  if (parent && ts.isPropertyAssignment(parent) && ts.isIdentifier(parent.name)) return parent.name.text;
  return null;
}

const files = {};
const functions = {};
for (const dir of dirs) {
  for (const file of sources(path.resolve(dir))) {
    const rel = path.relative(root, file).split(path.sep).join("/");
    const text = readFileSync(file, "utf8");
    files[rel] = text.split("\n").length - (text.endsWith("\n") ? 1 : 0);
    const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
    const seen = {};
    const visit = (node, scope) => {
      let next = scope;
      const callable =
        ts.isFunctionDeclaration(node) ||
        ts.isMethodDeclaration(node) ||
        ts.isFunctionExpression(node) ||
        ts.isArrowFunction(node);
      if (callable) {
        const name = nameOf(node);
        if (name) {
          next = scope ? `${scope}.${name}` : name;
          const start = source.getLineAndCharacterOfPosition(node.getStart(source)).line;
          const end = source.getLineAndCharacterOfPosition(node.getEnd()).line;
          const key = `${rel}::${next}`;
          seen[key] = (seen[key] ?? 0) + 1;
          functions[seen[key] > 1 ? `${key}#${seen[key]}` : key] = end - start + 1;
        }
      }
      ts.forEachChild(node, (child) => visit(child, next));
    };
    visit(source, "");
  }
}
process.stdout.write(JSON.stringify({ files, functions }));
