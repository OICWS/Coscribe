import { STACK, setStyle, styleOf } from "../../lib/slideSource";
import { setDirection } from "../../lib/slideStacks";
import { MenuField, NumberField, Row, Section, Segmented } from "./PropertyRows";
import type { EditorSelection } from "./SlideTextProperties";

const ALIGNS = ["start", "center", "end", "stretch"];
const JUSTIFIES = ["start", "center", "end", "between"];
const label = (value: string) => `${value[0].toUpperCase()}${value.slice(1)}`;
const px = (el: Element, name: string) => Number.parseFloat(styleOf(el, name) ?? "");
const number = (value: number, fallback: number) => (Number.isFinite(value) ? value : fallback);

/** A container's layout: its direction, the space between and around what it holds, and how that
 * is placed along and across it. Its card (background, border, radius, opacity) is the shape panel. */
export function ContainerProperties({ selection }: { selection: EditorSelection }) {
  const { element: stack, edit } = selection;
  const row = stack.getAttribute("data-layout") === "row";
  const choice = (name: string, options: string[], fallback: string) => {
    const current = styleOf(stack, name) ?? fallback;
    return <MenuField label={label(name)} value={label(current)} entries={options.map((o) => ({ label: label(o), checked: o === current, onSelect: () => edit((el) => setStyle(el, name, o)) }))} />;
  };
  return (
    <Section title="Layout">
      <Row label="Direction">
        <Segmented
          label="Direction"
          value={row ? "row" : "column"}
          choices={[
            { value: "row", title: "Row", icon: <span className="text-xs">Row</span> },
            { value: "column", title: "Column", icon: <span className="text-xs">Column</span> },
          ]}
          onChange={(direction) => edit((el) => setDirection(el, direction === "row"))}
        />
      </Row>
      <Row label="Gap">
        <NumberField label="Gap" unit="px" value={number(px(stack, "gap"), 0)} onCommit={(n) => edit((el) => setStyle(el, "gap", n > 0 ? `${Math.round(n)}px` : null))} />
      </Row>
      <Row label="Padding">
        <NumberField label="Padding" unit="px" value={number(px(stack, "padding"), 0)} onCommit={(n) => edit((el) => setStyle(el, "padding", n > 0 ? `${Math.round(n)}px` : null))} />
      </Row>
      <Row label="Align">{choice("align", ALIGNS, "stretch")}</Row>
      <Row label="Justify">{choice("justify", JUSTIFIES, "start")}</Row>
    </Section>
  );
}

/** What an element placed by a container asks of it: a share of the room, and a size of its own. */
export function ChildSizing({ selection }: { selection: EditorSelection }) {
  const { element: el, edit } = selection;
  if (el.parentElement?.localName !== STACK) return null;
  const size = (name: string, label: string) => (
    <Row label={label}>
      <NumberField label={`${label} (0 is automatic)`} unit="px" value={number(px(el, name), 0)} onCommit={(n) => edit((child) => setStyle(child, name, n > 0 ? `${Math.round(n)}px` : null))} />
    </Row>
  );
  return (
    <Section title="Size in the container">
      <Row label="Grow">
        <NumberField label="Grow" value={number(px(el, "flex-grow"), 0)} onCommit={(n) => edit((child) => setStyle(child, "flex-grow", n > 0 ? String(n) : null))} />
      </Row>
      <Row label="Shrink">
        <NumberField label="Shrink" value={number(px(el, "flex-shrink"), 1)} onCommit={(n) => edit((child) => setStyle(child, "flex-shrink", n === 1 ? null : String(Math.max(0, n))))} />
      </Row>
      {size("flex-basis", "Basis")}
      {size("width", "Width")}
      {size("height", "Height")}
    </Section>
  );
}
