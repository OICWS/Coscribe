# Keep the empty Side chat input at one line

The side chat used to measure the textarea while its dock was still hidden. The measurement
could set the height to zero until the person typed. CSS now sizes the input as it is laid
out, with a one-line minimum and a maximum for long messages.

The Side chat browser test checks that the empty input can take focus with a full line and
no scrollbar, and that multiline text grows the input.
