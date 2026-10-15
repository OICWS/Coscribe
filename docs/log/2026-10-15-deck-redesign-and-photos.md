# PowerPoint: redesigning a user's deck, licensed photos, and a picture bug (shipped)

Why: reviewing the office-route plan against ppt-master left two gaps: redesigning a deck the
user made ("帮我美化一下", common when a user drafts first and polishes after) and photos for a
photo-led style. ppt-master redesigns from an inventory of each slide, not by lifting slides back
to SVG (its 20k-line PPTX-to-SVG code), so the evaluation decided what to build.

## Shipped
- Evaluation task 15: a rough six-slide draft (default theme, a wall of text, two photos dropped
  in, a native chart, a table, a logo), built by `evals/pptx/make_inputs.py` with the photos only
  inside the deck; the brief asks to keep every text, number, photo, chart and table. Its check
  `pictures_of` compares each picture of the input deck with the result's (32-pixel thumbnails,
  so a re-saved or cropped copy counts and a different picture does not), where `pictures_min`
  only counted them.
- `read_pptx` shows a chart's data and the pictures on a slide; the slide came back empty for a
  chart and said nothing of pictures. The reader moves to `office/pptx/reading.py`.
- A .pptx given as a source to the number check gives its charts' numbers too.
- The compiler syncs a group's counters back after converting it: two pictures in sibling groups
  both got `rId2`, so a slide showed the last picture twice. This affected any page with two
  grouped pictures, not only a redesign.
- The PPTX Pages skill: how to redesign a user's deck (read everything, save its pictures, pass
  the old deck as a source, write a new file) and when to use photos (the user's own first;
  `search_licensed_images` only for a photo-led style, never the unlicensed `search_images`;
  a credit line for an attribution-required image).

## Checked
Task 15 (DeepSeek, effort low), each run 28/28 facts and no invented number:

| run | change | minutes | yuan | builds | pictures kept |
|---|---|---|---|---|---|
| 0 | `main` | 7.2 | 0.43 | 5 | 3 of 3 |
| 1 | reader + skill | 12.9 | 0.72 | 9 | 1 of 3: photos cut from a rendered slide |
| 2 | + chart numbers from a deck source | 8.9 | 0.52 | 4 | 2 of 3: the team photo twice |
| 3 | + the group fix | 5.3 | 0.33 | 3 | 3 of 3 |

Run 1's extra builds were the number check flagging the old deck's chart values (fixed in run
2); run 2's swapped photo was the compiler bug (the saved files and the page were right). One
run each: the times vary from run to run.

## Not verified
- The redesigned deck in PowerPoint on Windows (sent to the maintainer).
- A photo-led deck with downloaded licensed photos: no evaluation task asks for one yet.
