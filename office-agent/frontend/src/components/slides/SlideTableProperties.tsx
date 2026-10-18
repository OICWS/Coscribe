import { boxOf, hexColour, setStyle, styleOf } from "../../lib/slideSource";
import { clearColumnWidths, columnCount, columnWidths, hasHeader, setColumnCount, setColumnWidth, setHeader, setRowCount, tableRows } from "../../lib/slideTable";
import { familyName, setSize, type DesignSystem } from "../../lib/slideText";
import { ColourField, MenuField, NumberField, Row, Section } from "./PropertyRows";
import type { EditorSelection } from "./SlideTextProperties";

const DEFAULT_FONT = "Microsoft YaHei, Arial";

/** A table's properties: its size, header row and column widths, and the text, fill and border
 * colour it is drawn with. */
export function TableProperties({ selection, design }: { selection: EditorSelection; design: DesignSystem | null }) {
  const { element: table, edit } = selection;
  const colours = design?.palette ?? [];
  const width = boxOf(table)?.[2] ?? 960;
  const { widths, set } = columnWidths(table, width);
  const font = styleOf(table, "font-family") ?? styleOf(table.ownerDocument.documentElement, "font-family") ?? DEFAULT_FONT;
  const fonts = design?.fonts.includes(font) ? design.fonts : [font, ...(design?.fonts ?? [])];
  return (
    <>
      <Section title="Table">
        <Row label="Columns">
          <NumberField label="Columns" value={columnCount(table)} onCommit={(n) => edit((el) => setColumnCount(el, n))} />
        </Row>
        <Row label="Rows">
          <NumberField label="Rows" value={tableRows(table).length} onCommit={(n) => edit((el) => setRowCount(el, n))} />
        </Row>
        <Row label="Header row">
          <input
            type="checkbox"
            aria-label="Header row"
            className="h-4 w-4"
            checked={hasHeader(table)}
            onChange={(e) => edit((el) => setHeader(el, e.target.checked, colours[0] ?? "#1F2937"))}
          />
        </Row>
        <div className="text-sm text-[var(--muted)]">Column widths</div>
        <div className="grid grid-cols-2 gap-2">
          {widths.map((w, i) => (
            <NumberField key={i} label={`Column ${i + 1} width`} unit="px" value={w} onCommit={(n) => edit((el) => setColumnWidth(el, i, n, width))} />
          ))}
        </div>
        {set && (
          <button type="button" className="text-sm text-[var(--accent)]" onClick={() => edit(clearColumnWidths)}>
            Share the width evenly
          </button>
        )}
      </Section>
      <Section title="Text">
        <Row label="Font">
          <MenuField label="Font" value={familyName(font)} entries={fonts.map((f) => ({ label: familyName(f), checked: f === font, onSelect: () => edit((el) => setStyle(el, "font-family", f)) }))} />
        </Row>
        <Row label="Size">
          <NumberField label="Size" unit="px" value={Number.parseFloat(styleOf(table, "font-size") ?? "") || 24} onCommit={(n) => edit((el) => setSize(el, n))} />
        </Row>
        <Row label="Color">
          <ColourField
            label="Text colour"
            value={hexColour(styleOf(table, "color") ?? "")}
            colours={colours}
            onPick={(c) => edit((el) => setStyle(el, "color", c))}
            onClear={() => edit((el) => setStyle(el, "color", null))}
          />
        </Row>
      </Section>
      <Section title="Appearance">
        <Row label="Background">
          <ColourField
            label="Background"
            value={hexColour(styleOf(table, "background") ?? "")}
            colours={colours}
            onPick={(c) => edit((el) => setStyle(el, "background", c))}
            onClear={() => edit((el) => setStyle(el, "background", null))}
          />
        </Row>
        <Row label="Border">
          <ColourField
            label="Border colour"
            value={hexColour(styleOf(table, "border-color") ?? "")}
            colours={colours}
            onPick={(c) => edit((el) => setStyle(el, "border-color", c))}
            onClear={() => edit((el) => setStyle(el, "border-color", null))}
          />
        </Row>
      </Section>
    </>
  );
}
