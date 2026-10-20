import { CHART_TYPES, chartTitle, chartType, isStacked, seriesOf, setChartTitle, setChartType, setLabels, setLegend, setSeriesColour, setStacked, showsLabels, showsLegend } from "../../lib/slideChart";
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
        <Row label="Title">
          <label className={field}>
            <input
              aria-label="Chart title"
              className="h-full min-w-0 flex-1 bg-transparent outline-none"
              defaultValue={title}
              key={title}
              onBlur={(e) => e.target.value !== title && redraw((el) => setChartTitle(el, e.target.value))}
              onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
            />
          </label>
        </Row>
        <Row label="Legend">{toggle("Legend", showsLegend(chart), setLegend)}</Row>
        <Row label="Data labels">{toggle("Data labels", showsLabels(chart), setLabels)}</Row>
      </Section>
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
