# A message with a picture or a file can be sent while a reply is being worked on (shipped)

Why: while the agent was working, the composer took plain text only. A message with an image (or
a file) attached could not be sent until the reply ended, so the person had to wait to show what
they meant.

## Shipped
- The composer sends a message with attachments mid-turn the same way as text: as a note the
  model reads before its next step (`Composer.tsx`, `lib/steerNotes.ts`). Pictures travel on the
  `steer` message as data URLs (`SteerOut.images` in `conversation/wire.py`); the model gets them
  as image blocks in the note (`steer_message` in `runtime_lg/messages.py`). A file goes as the
  usual note naming its workspace path.
- A note's pictures and files show as cards on its bubble, live and after a reload
  (`SteerEntry.files`); taking a note back, or Stop, puts its text and attachments back in the
  composer; "Send now" and a note the turn ended before reading send them with the message.
- Plain text still answers a waiting question or approval card; a message with attachments waits
  as a note instead, since a card's answer carries text only.
- Tests: `test_a_note_sent_mid_turn_brings_its_pictures_to_the_model_lg`,
  `test_a_note_with_a_picture_no_turn_read_is_sent_with_it_lg`,
  `test_a_note_added_mid_turn_shows_its_pictures_and_files_in_the_log`, and reducer tests for a
  note's attachments when pending and requeued.

## Not verified
- In the desktop app on Windows: pasting or dropping a picture mid-turn and seeing the model use it.
