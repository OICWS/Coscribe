# Cut script output is kept whole in a file the conversation can read (shipped)

Why: a Python or Node script's stdout over 20,000 characters came back as its first and last
4,000 characters, and the middle was gone; the model could only run the script again to see it.

## Shipped
- `tools/_output_truncation.py`: `truncate_script_output` takes a folder; when it cuts, it writes
  the whole text there first and the cut marker names the file.
- `tools/exec/running.py`: `Detachable.cut_output_dir` is the conversation's folder for it
  (`<state_dir>/script-output/<thread>`); `timed_out_result` is the timed-out result both script
  tools shared as copies.
- `run_python_script`, `run_node_script` keep their cut stdout (and both streams on a timeout).
- `coordinator.py`: the file tools may read that folder, so `read_file` (head/tail) and
  `search_files` reach it. Only the file tools: scripts and the other tools do not.
- Tests: `tests/test_output_truncation.py` (the file holds the whole text and the marker names
  it; nothing is written under the cap; the conversation's `read_file` reads it).

## Not verified
- On Windows with the AppContainer: the folder is read by coscribe's own file tools, not by a
  script, so the container's grants are unchanged.

## Follow-ups
- Old files in `script-output/` are not cleaned up; they go with the state folder.
