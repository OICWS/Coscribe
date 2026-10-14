# PowerPoint part 2: native charts and tables on a page (shipped)

Why: a chart drawn with shapes cannot be changed in PowerPoint (its bars are rectangles), and a
drawn table is a grid of text boxes. Decision 0010 lists native charts and tables from data for
part 2; ppt-master already has them (MIT), so they are copied, not rewritten.

## Shipped
- Uses ppt-master's native chart and table objects, copied unchanged in the previous PR
  (`2026-10-14-deck-native-objects-copy.md`).
- `engine/native.py`: a page's `<g data-pptx-replace-with="chart">` (or `"table"`) holding one
  `<metadata type="application/json">` becomes a PowerPoint chart or table. The page writes the
  data only, no drawn copy beside it, so the compiler marks the JSON as the authority (upstream's
  default asks for a drawn fallback and a hash binding the two). A chart's parts (chart XML, its
  workbook) are added to the package under names it has free, its relationships rebuilt; a
  broken marker is an error naming the group, and the rest of the page is built.
- The checker's number check reads charts' categories and values and tables' cells.
- `build_pptx_from_pages`' description and "PPTX Pages" say how: a short chart and table example
  with the fields that matter (type, series, point colours, number format, font size, colours;
  cells with alignment and emphasis).
- `tests/test_deck_engine_native.py` (5 tests, all fail without it): a chart with its data in a
  workbook, charts on two pages keep their own parts, a table, a broken marker, the number check.

## Checked (2026-10-14, off-peak)
Tasks 01, 05 and 09, the ones with figures and tables, `deepseek-flash` at effort low, 3 judge
rounds; before is the same task's last run (01, 09 in the measurement, 05 on the cut prompt).

| Task | Native objects | Facts | Design | Content | Coherence | Output tokens | Cost |
|---|---|---|---|---|---|---|---|
| 01-q3-review | 2 charts, 2 tables | 19/19 | 4.30 (4.33) | 4.43 (4.50) | 4.53 (4.57) | 27k (52k) | 0.029 (0.048) |
| 05-long-report | 3 charts | 22/23 | 4.27 (4.27) | 4.30 (4.43) | 4.33 (4.57) | 44k (35k) | 0.043 (0.028) |
| 09-dense-table | 1 chart, 1 table | 36/36 | 4.30 (4.40) | 4.63 (4.53) | 4.53 (4.43) | 21k (41k) | 0.025 (0.042) |

- Every task used native objects; scores are level within the judge's spread; on 01 and 09
  the output tokens halved and the cost fell by 40%. 05 cost more than its last run but less
  than in the measurement (0.050): its cost varies more from run to run than the others.
- 05's missing fact is "41%": the chart holds 41 under the format "0", so it shows "41" and the
  number is not in any text. The guide now gives `0"%"` for a share and asks for the finding with
  its figure in the text above the chart. 09's chart of growth rates put the city names on the
  negative bars; the guide now gives `label_position: "low"` for negative values (both checked
  by compiling and rendering a page).
- The run and its judge cost 0.113 dollars, about 0.76 yuan.

## Not verified
- Windows and PowerPoint itself (LibreOffice renders them; the parts follow upstream, which is
  checked on PowerPoint there).
- The two guide changes above were not run with the model again.
