# Doc artifact, step 4d part 2: pictures in the editor

Date: 2026-10-27
Area: frontend

The toolbar's Picture button, a picture pasted (a screenshot) or dropped (a file) keeps the file in
the Doc's `assets/` folder (`POST /doc/asset`, part 1) and puts `![name](plan.doc/assets/name.png)`
in a paragraph of its own; the editor shows it from `GET /doc/asset`, while the file keeps the short
path, so the Doc and its folder can be moved together. A web address or inline data in a picture is
shown from where it is. PNG, JPEG, GIF and WebP up to 8 MB; the server says why when it refuses one.

Not verified: a real Windows machine; a picture dragged inside the page to move it (moving a block is
a delete and an insert, as for any block); a Doc moved or duplicated keeps its pictures only once the
artifact menu moves the side folder (step 5); the editor still opens only through a local change to
`isViewable`.
