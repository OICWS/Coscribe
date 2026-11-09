import { defaultKeymap } from "@codemirror/commands";
import { foldGutter, foldKeymap, HighlightStyle, indentUnit, LanguageDescription, syntaxHighlighting } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { highlightSelectionMatches, search, searchKeymap } from "@codemirror/search";
import { Compartment, EditorState } from "@codemirror/state";
import { drawSelection, EditorView, highlightActiveLine, keymap, lineNumbers } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";
import { useEffect, useRef } from "react";

// Colours are the app's CSS variables (index.css), so the light and dark themes both read.
const highlight = HighlightStyle.define([
  { tag: [t.keyword, t.operatorKeyword, t.modifier, t.controlKeyword, t.definitionKeyword], color: "var(--code-keyword)" },
  { tag: [t.string, t.special(t.string), t.regexp, t.inserted], color: "var(--code-string)" },
  { tag: [t.comment, t.lineComment, t.blockComment, t.meta, t.processingInstruction], color: "var(--code-comment)", fontStyle: "italic" },
  { tag: [t.number, t.bool, t.null, t.atom, t.literal], color: "var(--code-number)" },
  { tag: [t.propertyName, t.attributeName, t.tagName, t.deleted], color: "var(--code-property)" },
  { tag: [t.function(t.variableName), t.function(t.propertyName), t.labelName, t.link, t.url], color: "var(--code-function)" },
  { tag: [t.typeName, t.className, t.namespace, t.annotation], color: "var(--code-type)" },
  { tag: t.heading, color: "var(--code-function)", fontWeight: "600" },
  { tag: t.strong, fontWeight: "600" },
  { tag: t.emphasis, fontStyle: "italic" },
  { tag: t.monospace, color: "var(--code-string)" },
]);

const theme = EditorView.theme({
  "&": { height: "100%", fontSize: "13px", backgroundColor: "transparent", color: "var(--fg)" },
  "&.cm-focused": { outline: "none" },
  ".cm-scroller": { fontFamily: "var(--font-mono)", lineHeight: "1.7" },
  ".cm-gutters": { backgroundColor: "transparent", border: "none", color: "var(--muted)" },
  ".cm-lineNumbers .cm-gutterElement": { padding: "0 6px 0 14px", minWidth: "36px" },
  ".cm-foldGutter .cm-gutterElement": { padding: "0 4px", cursor: "pointer" },
  ".cm-activeLine": { backgroundColor: "color-mix(in srgb, var(--fg) 4%, transparent)" },
  ".cm-content": { caretColor: "var(--fg)", padding: "8px 0" },
  ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": { backgroundColor: "color-mix(in srgb, var(--accent) 22%, transparent) !important" },
  ".cm-selectionMatch": { backgroundColor: "color-mix(in srgb, var(--accent) 14%, transparent)" },
  ".cm-panels": { backgroundColor: "var(--card-bg)", color: "var(--fg)", borderColor: "var(--border)" },
  ".cm-searchMatch": { backgroundColor: "color-mix(in srgb, var(--warning) 35%, transparent)" },
});

/** Highlighted source with line numbers and folding: read only, but selectable and searchable
 * (Ctrl+F), so a person can find and copy a line. */
export default function CodeView({ text, name, wrap }: { text: string; name: string; wrap: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const language = useRef(new Compartment());

  useEffect(() => {
    const editor = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: text,
        extensions: [
          EditorState.readOnly.of(true),
          lineNumbers(),
          foldGutter({ openText: "⌄", closedText: "›" }),
          drawSelection(),
          highlightActiveLine(),
          highlightSelectionMatches(),
          search({ top: true }),
          keymap.of([...defaultKeymap, ...searchKeymap, ...foldKeymap]),
          wrap ? EditorView.lineWrapping : [],
          indentUnit.of("  "),
          syntaxHighlighting(highlight),
          theme,
          language.current.of([]),
        ],
      }),
    });
    view.current = editor;
    return () => editor.destroy();
  }, [text, wrap]);

  useEffect(() => {
    const description = LanguageDescription.matchFilename(languages, name);
    let cancelled = false;
    void description?.load().then((support) => {
      if (!cancelled) view.current?.dispatch({ effects: language.current.reconfigure(support) });
    });
    return () => {
      cancelled = true;
    };
  }, [name, text]);

  return <div ref={host} className="h-full min-h-0" data-testid="code-view" />;
}
