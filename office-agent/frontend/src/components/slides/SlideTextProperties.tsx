import {
  applyTextStyle,
  familyName,
  setAlign,
  setBold,
  setFill,
  setFont,
  setItalic,
  setLetterSpacing,
  setLineHeight,
  setList,
  setPadding,
  setSize,
  setUnderline,
  textValues,
  type DesignSystem,
  type ListKind,
  type TextAlign,
} from "../../lib/slideText";
import { AlignIcon, ItalicIcon, ListIcon, NumberedListIcon, UnderlineIcon } from "./formatIcons";
import { ColourField, MenuField, NumberField, Row, Section, Segmented } from "./PropertyRows";
import { setStyle } from "../../lib/slideSource";

/** The element selected in the editor, and the way to change it: `edit` runs on the element in the
 * editor's section, which draws and saves it. */
export interface EditorSelection {
  kind: "text" | "table";
  element: Element;
  edit: (change: (element: Element) => void) => void;
}

const ALIGNS: TextAlign[] = ["left", "center", "right", "justify"];
const LISTS: { value: ListKind; title: string }[] = [
  { value: "none", title: "No list" },
  { value: "bullet", title: "Bulleted list" },
  { value: "numbered", title: "Numbered list" },
];

/** A text box's properties: layout, text and appearance. What the .pptx cannot carry is not offered. */
export function TextProperties({ selection, design }: { selection: EditorSelection; design: DesignSystem | null }) {
  const v = textValues(selection.element);
  const edit = selection.edit;
  const fonts = design?.fonts.includes(v.font) ? design.fonts : [v.font, ...(design?.fonts ?? [])];
  const named = design?.styles.find((s) => s.id === v.styleId);
  return (
    <>
      <Section title="Layout">
        <Row label="Padding">
          <NumberField label="Padding" unit="px" value={v.padding} onCommit={(n) => edit((el) => setPadding(el, n))} />
        </Row>
      </Section>
      <Section title="Text">
        <Row label="Text style">
          <MenuField
            label="Text style"
            value={named?.name ?? "Custom"}
            entries={(design?.styles ?? []).map((s) => ({
              label: s.name,
              hint: `${s.size}`,
              checked: s.id === v.styleId,
              onSelect: () => edit((el) => void applyTextStyle(el, s)),
            }))}
          />
        </Row>
        <Row label="Font">
          <MenuField label="Font" value={familyName(v.font)} entries={fonts.map((f) => ({ label: familyName(f), checked: f === v.font, onSelect: () => edit((el) => setFont(el, f)) }))} />
        </Row>
        <Row label="Weight">
          <MenuField
            label="Weight"
            value={v.bold ? "Bold" : "Regular"}
            entries={[
              { label: "Regular", checked: !v.bold, onSelect: () => edit((el) => setBold(el, false)) },
              { label: "Bold", checked: v.bold, onSelect: () => edit((el) => setBold(el, true)) },
            ]}
          />
        </Row>
        <Row label="Size">
          <NumberField label="Size" unit="px" value={v.size} onCommit={(n) => edit((el) => setSize(el, n))} />
        </Row>
        <Row label="Spacing">
          <NumberField label="Line height" value={v.lineHeight} onCommit={(n) => edit((el) => setLineHeight(el, n))} />
          <NumberField label="Letter spacing" unit="px" value={v.letterSpacing} onCommit={(n) => edit((el) => setLetterSpacing(el, n))} />
        </Row>
        <Row label="Color">
          <ColourField label="Text colour" value={v.colour} colours={design?.palette ?? []} onPick={(c) => edit((el) => setStyle(el, "color", c))} />
        </Row>
        <Row label="Emphasis">
          <div className="flex gap-1">
            <Toggle label="Italic" on={v.italic} onClick={() => edit((el) => setItalic(el, !v.italic))} icon={<ItalicIcon className="h-4 w-4" />} />
            <Toggle label="Underline" on={v.underline} onClick={() => edit((el) => setUnderline(el, !v.underline))} icon={<UnderlineIcon className="h-4 w-4" />} />
          </div>
        </Row>
        <Row label="List">
          <Segmented
            label="List"
            value={v.list}
            choices={LISTS.map((l) => ({ ...l, icon: l.value === "none" ? <span className="text-xs">None</span> : l.value === "bullet" ? <ListIcon className="h-4 w-4" /> : <NumberedListIcon className="h-4 w-4" /> }))}
            onChange={(list) => edit((el) => void setList(el, list))}
          />
        </Row>
        <Row label="Align">
          <Segmented
            label="Align"
            value={v.align}
            choices={ALIGNS.map((a) => ({ value: a, title: `Align ${a}`, icon: <AlignIcon align={a} className="h-4 w-4" /> }))}
            onChange={(align) => edit((el) => setAlign(el, align))}
          />
        </Row>
      </Section>
      <Section title="Appearance">
        <Row label="Background">
          <ColourField
            label="Background"
            value={v.background}
            colours={design?.palette ?? []}
            onPick={(c) => edit((el) => setFill(el, c))}
            onClear={() => edit((el) => setFill(el, null))}
          />
        </Row>
      </Section>
    </>
  );
}

function Toggle({ label, on, icon, onClick }: { label: string; on: boolean; icon: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={on}
      className={`flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] ${on ? "bg-[var(--card-bg)] text-[var(--fg)]" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}
      onClick={onClick}
    >
      {icon}
    </button>
  );
}
