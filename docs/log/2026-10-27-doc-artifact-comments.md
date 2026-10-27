# Doc artifact, step 3: comments

Date: 2026-10-27
Area: tools, server

Step 3 of decision 0025, as a deck's comments are (0015). `GET`, `POST` and `DELETE`
`/api/threads/{id}/doc/comments`, `.../{id}/replies` and `.../{id}` (resolve or reopen) read, add,
answer, resolve and delete comments kept in `name.doc/comments.json`. A comment is anchored to the
text of its block and which copy of that text it is, not to the block's number: coscribe or the
person can add or remove blocks and the comment follows its block, or is returned with
`detached: true` and `block: null` when the text is gone (it is kept). A reply with `from_coscribe`
is written under the author `coscribe`; another reply under the computer's user, as a deck's.

The design note said four deferred tools and a next-turn note. A deck's comments have neither: the
editor sends a comment for coscribe as a chat message and writes the turn's answer back as a reply.
The Doc does the same, so there is no new tool and the tool list stays fixed (0001); the note was
corrected.

Not verified: the whole flow with an editor (step 4); a Doc that is renamed, moved or duplicated
keeps its comments only once the artifact menu moves the side folder (step 5).
