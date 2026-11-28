# A file the agent's own script changed is not taken for the person's edit (shipped)

Why: on the OmegaUse-OfficeVal runs (#1078) the edit guard refused about 33 writes. In each case
the file had last been changed by one of the agent's own `run_python_script` or
`run_node_script` calls, but the refusal said "changed in the app by the user". Each refusal cost
the agent another read and another model call, on a file nobody else had touched.

## Shipped
- `EditGuardMiddleware` takes the script tools, which are the EXEC ones. After each script call
  it records again what every file it has seen now holds. A later write is refused only for a
  change that came from outside the agent's own work.

## Not verified
- The desktop app on Windows. A person editing a file in the app while one of the agent's scripts
  is running is no longer caught; their edit has to land between the script and the next write.

## Follow-ups
- None.
