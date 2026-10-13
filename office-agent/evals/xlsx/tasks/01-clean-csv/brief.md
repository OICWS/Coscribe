orders_export.csv is a messy export from our order system. Clean it up into a workbook called orders_clean.xlsx with one sheet named Orders.

- Header row: Order Date, Customer, Category, Amount (no stray spaces), in bold.
- Order Date holds real dates, shown as yyyy-mm-dd; Amount holds real numbers, shown with a thousands separator and two decimals (#,##0.00), no currency signs.
- Category in Title Case without stray spaces (Hardware, Software, Services); Customer without stray spaces.
- No blank rows and no duplicate orders.
- Sorted by Order Date, oldest first; orders on the same day keep the order they had in the file.
