---
title: Excel workbooks
description: Have coscribe read, clean, total and reconcile spreadsheets, and build workbooks with formulas and charts.
---

coscribe reads `.xlsx` files sheet by sheet and writes real workbooks: cells, styles, formulas and native Excel charts.

## What to ask for

- **Clean and total**: "Remove the rows without a shipping address and total the amounts by supplier."
- **Reconcile**: "Match the bank export against our ledger and list what doesn't agree."
- **Build a model**: "Make a 12-month budget with a summary sheet that adds up the departments."
- **Chart it**: "Add a column chart of revenue by region next to the table."

Name the files and the sheets if a workbook has several, and say what the result should be: a new file, a new sheet, or a change to the existing one.

## Formulas stay formulas

When a value depends on other cells, coscribe writes it as an Excel formula, so the workbook keeps working when you change a number. It also calculates the formulas and saves their results in the file, so the values show even in programs that don't recalculate on opening.

## Large or unusual jobs

For work the built-in tools don't cover, coscribe can write a Python script (with `pandas` and `openpyxl`, for example) and run it, with your approval. See [Approvals and permission modes](../use/approvals.md).

> [!TIP]
> Want coscribe to follow your team's conventions, such as colors for inputs and outputs or a number format? Put them in your [instructions](../customize/instructions.md) or a [skill](../customize/skills.md).
