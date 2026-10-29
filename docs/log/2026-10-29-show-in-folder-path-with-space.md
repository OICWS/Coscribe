# "Show in folder" opens the file's folder when its path has a space (shipped)

Why: the maintainer worked in a folder of their own; "Show in folder" on the deck's card and in
the task details opened Documents instead. Explorer was started with the argument list
`["explorer", "/select,<path>"]`. For a path with a space (a OneDrive folder such as
`OneDrive - Company` has one), Python quotes the whole `/select,...` argument. Explorer doesn't
parse that and opens its default folder.

## Shipped
- Explorer gets `explorer /select,"<path>"` as one command line, quoting only the path.

## Not verified
- On a real Windows machine. Reasoning plus a unit test of the command line only.
