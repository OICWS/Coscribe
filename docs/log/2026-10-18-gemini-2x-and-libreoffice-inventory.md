# Gemini 2.x effort is not built; the LibreOffice inventory (shipped)

Why: batch 10 items 5 and 6 (#425).

## Item 5: Gemini 2.x levels via `thinking_budget`
- Not built, closed with a reason. The live check on the free key (2026-10-18): `gemini-2.5-flash`,
  `gemini-2.5-flash-lite` and `gemini-2.5-pro` answer 404 "no longer available to new users", and
  `gemini-2.0-flash` "no longer available". Both through `langchain-google-genai` and a plain REST
  call with `thinkingBudget`. The models list still names 2.5, but a new key cannot call them, so
  no number for a budget could be checked and none is guessed.
- What works: `gemini-3.5-flash` through `with_effort(model, "ultra")` runs as `high`
  (levels `low, medium, high` from the library profile) and the call returns with
  `reasoning` tokens counted. This is the case #315 reported failing on 3.2.0.
- Reopen if a user brings a key that still has 2.5: the change is one branch in
  `runtime_lg/effort.py` that sets `thinking_budget`.

## Item 6: what still needs LibreOffice (decision 0012)
Every mention of `soffice` / LibreOffice outside the slide files, by kind:
- **Product code (`src/`): no call.** The remaining hits are comments naming how LibreOffice or
  Word reads a thing (`docx/_xml.py`, `table_layout.py`, `xlsx/column_widths.py`,
  `xlsx/engine_objects.py`, `_ooxml_validate.py`, `docx/__init__.py`, `presentations.py`,
  `_office_bins.py`, `runtime/secrets.py`) and keep their reason. Formula values go through IronCalc
  (`xlsx/calc.py`), deck page previews through resvg, PDF pages through pypdfium2
  (`pdf_pages.py`); conversion goes through Office (COM).
- **Evaluation: kept by the decision.** `evals/libreoffice.py` (the judge's renders), and the
  checks in `evals/{render,pptx_checks,xlsx_checks,tasks}.py`.
- **Tests: stand-in and independent reader.** `tests/libreoffice_probe.py` and the tests that skip
  without a working LibreOffice; they read a produced file with a second implementation. No
  replacement: that is what they are for.
- **Development script: `scripts/verify_pptx_quality.py`** converts a deck to PDF with `soffice`
  and `pdftoppm` for a person to look at. Kept: it has no product role, and a deck's own preview
  is already resvg (`slide_svg`).
- Fixed in passing: a frontend comment (`chatlog/helpers.ts`) said a thumbnail is rendered by
  LibreOffice.

## Not verified
- Nothing in the product path changed.
