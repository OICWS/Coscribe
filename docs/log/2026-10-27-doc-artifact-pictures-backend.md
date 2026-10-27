# Doc artifact, step 4d part 1: the Doc's pictures on the server

Date: 2026-10-27
Area: tools, server

`POST /api/threads/{id}/doc/asset` (a multipart `file` and the Doc's `path`) keeps a PNG, JPEG, GIF or
WebP picture of 8 MB at most in `name.doc/assets/` under a free name and returns `src`, the path the
markdown names it by (`name.doc/assets/chart.png`), and its size. `GET .../doc/asset?path=&src=` serves
one back with `nosniff`; only a file directly in that Doc's `assets/` folder is served, so a path with
`..`, another folder or another Doc's side folder is a 404. SVG is refused (a vector file can carry
script). The editor that uses them is part 2.

Not verified: a picture the person adds to a Doc that is then moved or duplicated keeps its picture only
once the artifact menu moves the side folder (step 5).
