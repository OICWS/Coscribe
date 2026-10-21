import {
  CHART_TYPES,
  NUMBER_FORMATS,
  axisTitle,
  chartTitle,
  chartType,
  isStacked,
  seriesOf,
  setAxisTitle,
  setChartTitle,
  setChartType,
  setLabels,
  setLegend,
  setSeriesColour,
  setStacked,
  setValueAxisSetting,
  showsLabels,
  showsLegend,
  valueAxisSetting,
  type Axis,
  type ValueAxisKey,
} from "../../lib/slideChart";
import type { DesignSystem } from "../../lib/slideText";
import { ColourField, MenuField, Row, Section, Segmented, field } from "./PropertyRows";
import type { EditorSelection } from "./SlideTextProperties";

const ON_OFF = [
  { value: "on", title: "On", icon: <span className="text-xs">On</span> },
  { value: "off", title: "Off", icon: <span className="text-xs">Off</span> },
];

/** A native chart's properties: what the .pptx chart carries and the engine writes into it. */
export function ChartProperties({ selection, design }: { selection: EditorSelection; design: DesignSystem | null }) {
  const { element: chart, edit } = selection;
  const type = chartType(chart);
  const title = chartTitle(chart);
  const redraw = (change: (el: Element) => void) => edit(change, true);
  /** A text field applied on Enter or blur; empty clears the setting. */
  const text = (label: string, value: string, apply: (el: Element, value: string) => void, placeholder?: string) => (
    <label className={field}>
      <input
        aria-label={label}
        className="h-full min-w-0 flex-1 bg-transparent outline-none"
        defaultValue={value}
        key={value}
        placeholder={placeholder}
        onBlur={(e) => e.target.value !== value && redraw((el) => apply(el, e.target.value))}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />
    </label>
  );
  const setting = (key: ValueAxisKey) => {
    const value = valueAxisSetting(chart, key);
    return typeof value === "number" || typeof value === "string" ? String(value) : "";
  };
  const bound = (key: "minimum" | "maximum", label: string) =>
    text(label, setting(key), (el, v) => setValueAxisSetting(el, key, v.trim() !== "" && Number.isFinite(Number(v)) ? Number(v) : null), "Auto");
  const axisTitleRow = (axis: Axis, label: string) => (
    <Row label={label}>{text(`${label} title`, axisTitle(chart, axis), (el, v) => setAxisTitle(el, axis, v))}</Row>
  );
  const format = setting("number_format");
  const toggle = (label: string, on: boolean, apply: (el: Element, on: boolean) => void) => (
    <Segmented label={label} value={on ? "on" : "off"} choices={ON_OFF} onChange={(v) => redraw((el) => apply(el, v === "on"))} />
  );
  return (
    <>
      <Section title="Chart">
        {type && (
          <Row label="Type">
            <MenuField
              label="Chart type"
              value={CHART_TYPES.find((t) => t.value === type)?.label ?? type}
              entries={CHART_TYPES.map((t) => ({ label: t.label, onSelect: () => redraw((el) => setChartType(el, t.value)) }))}
            />
          </Row>
        )}
        {(type === "column" || type === "bar") && <Row label="Stacked">{toggle("Stacked", isStacked(chart), setStacked)}</Row>}
        <Row label="Title">{text("Chart title", title, (el, v) => setChartTitle(el, v))}</Row>
        <Row label="Legend">{toggle("Legend", showsLegend(chart), setLegend)}</Row>
        <Row label="Data labels">{toggle("Data labels", showsLabels(chart), setLabels)}</Row>
      </Section>
      {type !== null && (
        <Section title="Axes">
          {axisTitleRow("category", "Category")}
          {axisTitleRow("value", "Value")}
          <Row label="Min">{bound("minimum", "Minimum")}</Row>
          <Row label="Max">{bound("maximum", "Maximum")}</Row>
          <Row label="Format">
            <MenuField
              label="Number format"
              value={NUMBER_FORMATS.find((f) => f.value === (format || null))?.label ?? format}
              entries={NUMBER_FORMATS.map((f) => ({ label: f.label, checked: f.value === (format || null), onSelect: () => redraw((el) => setValueAxisSetting(el, "number_format", f.value)) }))}
            />
          </Row>
        </Section>
      )}
      <Section title="Series colours">
        {seriesOf(chart).map((s, i) => (
          <Row key={i} label={s.name.length > 10 ? `${s.name.slice(0, 9)}…` : s.name}>
            <ColourField label={`${s.name} colour`} value={s.colour} colours={design?.palette ?? []} onPick={(c) => redraw((el) => setSeriesColour(el, i, c))} />
          </Row>
        ))}
      </Section>
    </>
  );
}
