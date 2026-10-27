# Doc artifact, step 4b: comments in the editor

Date: 2026-10-27
Area: frontend, server

Comments in the Doc editor, as a deck's are (0015). Selecting words shows "Comment" in the selection
bar: a box with the text and a "Send to coscribe" checkbox, unticked, so a comment can be made and
sent later with others. The top-right button shows all comments (a dot while some are open); its
panel has a filter (open, resolved, all), per comment the words it is on, the author, replies, Resolve
and a menu with Edit and Delete, and "Send N to coscribe" for the comments not sent yet. They go as
one message, and coscribe's answer is written as a reply under each of them (`CommentLink.alsoCommentIds`).
On the page the words a comment is on are shaded and the block has its count in the margin; the count
opens the comment. A comment is anchored to its block's text (step 3), so the marks follow the blocks
through saves, which refresh the comments.

Server: a comment keeps the `quote` it was made on, `PUT /doc/comments/{id}` changes its words,
`POST /doc/comments/{id}` takes `sent: true` as well as `resolved`.

Not verified: a real Windows machine; the editor still opens only through a local change to
`isViewable` (step 5 sends files to it); a comment on a block typed since the last save waits for the
save and says so if it has no place in the file yet. Pictures, callouts and charts are step 4c.
