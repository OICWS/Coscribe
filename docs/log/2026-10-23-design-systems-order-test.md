# The design-system order test no longer depends on Windows' clock (shipped)

Why: `test_the_list_is_newest_change_first` failed on the Windows job of #580 and #582. Windows'
clock moves in steps of about 15 ms, so the second create and the rename could share one
`updated_at`, and the sort then kept them in the order they were found.

## Shipped
- `tests/test_design_systems.py`: the test gives each write its own time through
  `design_systems._now`. The store is unchanged.

## Not verified
- Nothing beyond CI: the Windows job runs this test.
