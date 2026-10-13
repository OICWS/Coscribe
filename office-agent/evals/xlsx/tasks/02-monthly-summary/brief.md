transactions.xlsx has one sheet, Data, with the first quarter's spending: Date, Category, Amount. Add a sheet called Summary to the same workbook (keep Data as it is) with a table of spending by category and month:

- A1:E1 = Category, Jan, Feb, Mar, Total.
- A2:A4 = the three categories in alphabetical order; A5 = Total.
- B2:D4 = the amount of that category in that month, E = the row total, row 5 = the column totals (and E5 the grand total).

The summary must be driven by the Data sheet through formulas, not typed-in numbers: when someone changes an amount in Data, the Summary changes with it.
